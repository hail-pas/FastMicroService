import uuid

import faker


def gen_fake() -> faker.Faker:
    return faker.Faker(locale=["zh_CN"], seed=uuid.uuid4().int)
