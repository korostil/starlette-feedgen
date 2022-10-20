import aiofiles
import asyncio
import html
import re
from abc import ABC
from typing import Any
from starlette.applications import Starlette
from starlette_feedgen import FeedEndpoint
from starlette_feedgen.generator import Rss201rev2Feed
from starlette_feedgen.utils import SimplerXMLGenerator, rfc2822_date
import funcy
import uvicorn

from test_items import articles
from test_cached_items import cached_items

app = Starlette()


# Feed generators
class SXG(SimplerXMLGenerator):
    async def addQuickElementCDATA(
        self, name: str, content: str = None, attrs: dict = None
    ) -> None:
        await self.startElement(name, {})
        if content is not None:
            await self._write(f'<![CDATA[{content}]]>')
        await self.endElement(name)


class ExtendedFeed(Rss201rev2Feed):
    content_type: str = 'application/xml'

    async def write(self, outfile, encoding: str = 'utf-8') -> None:
        handler = SXG(outfile, encoding)
        await handler.startDocument()
        await handler.startElement('rss', self.rss_attributes())
        await handler.startElement('channel', self.root_attributes())
        await self.add_root_elements(handler)
        await self.cache_items(handler, encoding)
        # await self.write_items(handler)
        await self.endChannelElement(handler)
        await handler.endElement('rss')

    async def cache_items(self, handler: SXG, encoding: str) -> None:
        if self.use_cached_items:  # либо пишем полученные на лету данные, либо кэшированнные
            for item in self.cached_items:
                await handler._write(item)
        else:
            for item in self.items:
                await self.cache_item(item, handler, encoding)

    async def cache_item(self, item: dict, handler: SXG, encoding: str) -> None:
        async with aiofiles.tempfile.TemporaryFile("w+", newline="\n", encoding=encoding) as buf:
            cache_handler = SXG(buf, encoding)

            await cache_handler.startElement('item', self.item_attributes(item))
            await self.add_item_elements(cache_handler, item)
            await cache_handler.endElement('item')

            await buf.seek(0)
            string_result = await buf.read()
            bytes_result = string_result.encode(encoding)
            print(bytes_result)  # псевдо-кэширование (вывод байтов в консоль)
            # await opis_api.upload(
            #     file=buf, namespace=self.feed['name'], filename=f"{item['slug']}.xml"
            # )

            await buf.seek(0)
            await handler._write(await buf.read())  # из асинхронного буфера получаем строку методом read()

    def rss_attributes(self) -> dict:
        attrs: dict = super().rss_attributes()
        attrs['xmlns:media'] = 'http://search.yahoo.com/mrss/'
        return attrs

    def root_attributes(self) -> dict:
        attrs: dict = super().root_attributes()
        attrs['xmlns:content'] = 'http://purl.org/rss/1.0/modules/content/'
        return attrs


class YandexTurboRSSFeed(ExtendedFeed):
    def rss_attributes(self) -> dict:
        return {
            'version': self._version,
            'xmlns:yandex': 'http://news.yandex.ru',
            'xmlns:turbo': 'http://turbo.yandex.ru',
        }

    # сделал синхронным
    def item_attributes(self, item: dict) -> dict:
        return {'turbo': 'true'}

    # сделал синхронным
    def root_attributes(self) -> dict:
        return {}

    async def add_root_elements(self, handler: SXG) -> None:
        await handler.addQuickElement('title', self.feed['title'])
        await handler.addQuickElement('link', self.feed['link'])
        await handler.addQuickElement('description', self.feed['description'])
        await handler.addQuickElement(
            'yandex:analytics',
            attrs={'type': 'Yandex', 'id': ''},
        )
        await handler.addQuickElement(
            'turbo:analytics',
            attrs={'type': 'Google', 'id': ''},
        )

    async def add_item_elements(self, handler: SXG, item: dict) -> None:
        await handler.addQuickElement('turbo:extendedHtml', 'true')
        await handler.addQuickElement('link', item['link'])
        await handler.addQuickElement('author', item.get('author_name'))

        for category in item['categories']:
            await handler.addQuickElement('category', category)

        if item['pubdate'] is not None:
            await handler.addQuickElement('pubDate', rfc2822_date(item['pubdate']))

        await handler.addQuickElementCDATA('turbo:content', item['content'])


# Feed Endpoints
class AsyncFeed(FeedEndpoint, ABC):
    limit: int = 100
    offset: int = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.init_tasks = []

    async def get(self, request):
        # простая логика кэширования, в ютурне тут будем забирать из описа
        # self.use_cached_items = True
        # self.cached_items.extend(cached_items)

        await asyncio.gather(*self.init_tasks)
        response = await super().get(request)
        return response


class GenericFeed(AsyncFeed):
    author_email: str = 't@t.ru'
    author_name: str = 'Т-Ж'
    categories: list[str] = ['Финансы']
    description: str = 'sdfew'
    domain: str = 'test.ru'
    feed_type: Rss201rev2Feed = ExtendedFeed
    item_guid_is_permalink: bool = False
    language: str = 'ru-RU'
    link: str = 'tjsdgs'
    name: str = 'default'
    title: str = 'dfdsfew'
    utm_source: str = 'rss'

    article_exclude_flags: list[str] = []
    article_fields: list[str] = [
        'author',
        'date_modified',
        'date_published',
        'excerpt',
        'id',
        'legacy_path',
        'path',
        'share',
        'slug',
        'subtitle',
        'title',
    ]

    async def get_items(self):
        return articles

    def feed_url(self) -> str:
        return 'some-url'

    async def feed_extra_kwargs(self, obj) -> dict:
        return {'name': self.name}

    async def item_extra_kwargs(self, item) -> dict:
        return {'slug': item.slug}

    def item_title(self, item) -> str:
        return item.title

    def item_description(self, item):
        return item.excerpt or item.share.description

    def item_author_name(self, item) -> str:
        if not item.author or item.author.is_default:
            return self.author_email
        return item.author.full_name

    def item_guid(self, item) -> str:
        return str(item.id)

    def item_link(self, item) -> str:
        utm_postfix = ''
        if self.utm_source:
            utm_postfix = f'?utm_source={self.utm_source}'
        return item.absolute_url + utm_postfix

    async def _populate_feed(
        self, feed, item: Any, request_is_secure: bool = True
    ) -> None:
        """If the article has no content, it is excluded"""
        with funcy.suppress(Exception):
            await super()._populate_feed(feed, item, request_is_secure)

    async def item_pubdate(self, item):
        return item.date_published

    async def item_updateddate(self, item):
        return item.date_modified

    async def render_distilled_content(self, item, distilled) -> str:
        content = 'Distilled content'
        # flavor = '' if self.name == 'default' else self.name
        # try:
        #     content = await minerva_api.render(
        #         distilled, f'https://{settings.app_fqdn}/{item.slug}', flavor
        #     )
        # except FailedDependency as e:
        #     logger.error(e.detail, extra=e.extra)
        #     raise NoContent
        #
        # if not content:
        #     raise NoContent

        return content


@app.route('/feed')
class YandexTurboFeed(GenericFeed):
    feed_type = YandexTurboRSSFeed
    limit: int = 30
    name: str = 'yandexturbo'

    article_exclude_flags: list[str] = ['hidden_from_turbo', 'urania', 'ugc']
    article_fields: list[str] = [*GenericFeed.article_fields, 'content', 'cover']

    async def item_extra_kwargs(self, item) -> dict:
        item_extra_kwargs = await super().item_extra_kwargs(item)

        content = await self.render_header(item)
        content += ''.join(
            await asyncio.gather(
                self.render_content(item),
                self.render_recommendations(item),
                self.render_comments(item),
            )
        )

        return {'content': content, **item_extra_kwargs}

    async def item_author_name(self, item) -> str:
        if not item.author or item.author.is_default:
            return 'Редакция'
        return item.author.full_name

    @classmethod
    async def render_header(cls, item) -> str:
        try:
            cover = item.cover.cover_image.files['original'].filepath  # type: ignore
        except (KeyError, AttributeError):
            cover = ''

        return 'dsfdsf'

    async def render_content(self, item) -> str:
        return ''

        # distilled = distiller.deserialize(
        #     item.content.get('nodes', ()), finalize_nodes=True
        # )
        # self._on_before_content_render(distilled)
        # rendered = await self.render_distilled_content(item, distilled)
        # self._on_after_content_render(rendered)
        # return rendered

    @classmethod
    async def _on_before_content_render(cls, distilled) -> None:
        return
        # kinds_to_remove = {'bannerlink-level', 'quiz-banner', 'subscription-level'}
        # remove_nodes(
        #     distilled.nodes,
        #     conditions=(
        #         lambda node: node.kind in kinds_to_remove,
        #         lambda node: 'desktop-table' in getattr(node, 'class', ()),
        #     ),
        # )

    @classmethod
    async def _on_after_content_render(cls, content: str) -> str:
        content = cls._fix_links_for_turbo(content)
        content = cls._fix_marks_for_turbo(content)
        content = cls._remove_inline_classes(content)
        return content

    @classmethod
    async def _fix_links_for_turbo(cls, content: str) -> str:
        return content.replace('yandex.ru/turbo/', '')

    @classmethod
    async def _fix_marks_for_turbo(cls, content: str) -> str:
        return content

    @classmethod
    async def _remove_inline_classes(cls, content: str) -> str:
        return re.sub('<(.*?) style=".*?"(.*?)>', '<\\1\\2>', content)

    @classmethod
    async def render_recommendations(cls, item) -> str:
        return ''  # TODO

    async def render_comments(self, item) -> str:
        return 'sfwfw'
        # comments = await social_api.get_best_comments(
        #     item, limit=settings.yandexturbo_comments_limit
        # )
        # rendered_comments = '\n'.join(
        #     self._render_comment(comment) for comment in comments
        # )
        # return comments_block_template.format(
        #     article_link=self.item_link(item), comments=rendered_comments
        # )

    @classmethod
    async def _render_comment(cls, comment) -> str:
        return 'sefwgr'
        # author = {'author_name': 'Читатель', 'author_image': ''}
        # if comment.author:
        #     author = {
        #         'author_name': comment.author.name,
        #         'author_image': comment.author.image or '',
        #     }
        # return comment_template.format(
        #     date_added=comment.date_added.strftime('%d.%m.%Y'),
        #     text=cls._get_comment_text(comment),
        #     image=f'<img src="{comment.image.preview}">' if comment.image else '',
        #     **author,
        # )

    @classmethod
    async def _get_comment_text(cls, comment) -> str:
        if comment.status == 'deleted_by_author':
            text = 'Комментарий удален пользователем'
        elif comment.status == 'deleted_by_moderator':
            text = 'Комментарий удален модератором'
        elif comment.ban:
            text = 'Комментарий заблокирован'
        else:
            text = re.sub('(<.*?>)|&', '', html.unescape(comment.text))
        return text


if __name__ == '__main__':
    uvicorn.run(
        app,
        access_log=False,
        loop='uvloop',
        http='httptools',
        lifespan='on',
    )
