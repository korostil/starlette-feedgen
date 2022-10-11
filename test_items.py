from uuid import UUID
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, NoneStr, HttpUrl


# Author schema
class Author(BaseModel):
    first_name: str
    id: UUID | None
    last_name: NoneStr
    nickname: NoneStr

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name or ""}'.strip()

    @property
    def is_default(self) -> bool:
        return self.nickname == "editorial"


# Media schemas
class MediaFile(BaseModel):
    filepath: HttpUrl


class MediaObject(BaseModel):
    files: dict[str, MediaFile]
    originalBasename: str


class Cover(BaseModel):
    cover_image: MediaObject | str | None

    class Config:
        allow_mutation = False


# Shares schema
class Share(BaseModel):
    description: NoneStr
    og_image: NoneStr
    zen_categories: list[str] = []
    zen_image: NoneStr
    zen_title: NoneStr


# Article schemas
class Stats(BaseModel):
    id: UUID | None
    views: int = 0


class Article(BaseModel):
    author: Author | None
    config: dict = {}
    content: dict = {}
    cover: Cover | None
    date_modified: datetime
    date_published: datetime
    excerpt: NoneStr
    flows: list[str] = []  # Flow -> str
    id: UUID | None
    legacy_path: str
    path: str
    share: Share = Share()
    slug: str
    stats: Stats = Stats()
    subtitle: str = ""
    tags: list[str] = []  # Tag -> str
    title: str

    @property
    def absolute_url(self) -> str:
        return self.legacy_path  # qualify_url -> legacy_path


articles_data = [
    {
        "author": {"first_name": "Редакция", "last_name": "", "nickname": "editoral"},
        "content": {
            "ts": 1664886072,
            "schema_version": 3,
            "nodes": [
                {"kind": "p", "children": [{"kind": "text", "content": "Текст текст текст"}]}
            ],
        },
        "cover": {"cover_image": ""},
        "date_modified": datetime(2022, 10, 4, 15, 20, 53, 243117),
        "date_published": datetime(2022, 10, 4, 15, 17, 43, 437125),
        "id": UUID("8e3c73e1-095e-4da9-b05d-a6904ee82ceb"),
        "legacy_path": "/testovaia-statia-zaglushka-dlia-novogo-potoka-srav/",
        "path": "/testovaia-statia-zaglushka-dlia-novogo-potoka-srav/",
        "slug": "testovaia-statia-zaglushka-dlia-novogo-potoka-srav",
        "title": "Тестовая статья заглушка для нового потока Сравнятор",
    },
    {
        "author": {"first_name": "Анна Кондрашова", "last_name": "", "nickname": "kondrashova"},
        "content": {
            "ts": 1664447114,
            "schema_version": 3,
            "nodes": [
                {
                    "kind": "author",
                    "name": "Анна Кондрашова",
                    "description": [],
                    "image": {
                        "originalBasename": "8ff3f3f1.cg5n",
                        "files": {
                            "original": {
                                "filepath": "https://img-cdn.tinkoffjournal.ru/8ff3f3f1.cg5n",
                                "mimeType": "image/png",
                                "width": 160,
                                "height": 160,
                                "fileSize": 0,
                                "resourceType": "image",
                            }
                        },
                    },
                    "consultant": "",
                    "is_anonymous": False,
                    "is_deleted": False,
                    "link": "/user131647/",
                },
                {
                    "kind": "p",
                    "children": [
                        {
                            "kind": "text",
                            "content": "Появилось неожиданно много объявлений о\xa0продаже дач в\xa0Подмосковье. Некоторые публикуют люди, которые экстренно уехали за\xa0рубеж. Дачи показывают их\xa0родственники и\xa0соседи, а\xa0собственники обещают предоставить все необходимые доверенности к\xa0моменту сделки.",
                        }
                    ],
                },
                {
                    "kind": "p",
                    "children": [
                        {
                            "kind": "text",
                            "content": "Безопасно ли\xa0покупать дачу таким образом? Если да, что обязательно предусмотреть?",
                        }
                    ],
                },
                {
                    "kind": "feature",
                    "name": "poll",
                    "config": '{"answers":[{"icon":"👋","answer":"Жду ответа эксперта"}],"needLogin":true,"unitMeasure":["читатель","читателя","читателей"],"maxTotalIconsVisibleCount":100,"_attrs":{},"_extra":{}}',
                    "config_name": "poll-dacha-here-seller-abroad",
                    "bundle_url": "",
                    "placeholder": "",
                    "inline": False,
                    "ratio": None,
                    "version": 2,
                },
            ],
        },
        "cover": {"cover_image": ""},
        "date_modified": datetime(2022, 9, 29, 13, 26, 9, 63027),
        "date_published": datetime(2022, 9, 29, 13, 26, 5, 346966),
        "id": UUID("f78112bd-eac6-4ee8-96ad-bac8d3d1f110"),
        "legacy_path": "/dacha-here-seller-abroad/",
        "path": "/dacha-here-seller-abroad/",
        "slug": "dacha-here-seller-abroad",
        "title": "Безопасно ли\xa0покупать дачу у\xa0россиян, которые сейчас за\xa0рубежом?",
    },
]

articles = [Article(**article_data) for article_data in articles_data]
