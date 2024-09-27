import factory
from storages import enums
from storages.relational.models import Account, Company
from burnish_sdk_py.common.encrypt import PasswordUtil

from tests.factory.base import gen_fake


class AccountFactory(factory.Factory):
    class Meta:
        model = Account

    def extra_create(
        company: Company,
        status: enums.StatusEnum = enums.StatusEnum.enable,
        is_staff: bool = False,
        is_super_admin: bool = False,
        is_company_super_admin: bool = False,
    ):
        return Account(
            username=gen_fake().user_name(),
            password=PasswordUtil.get_password_hash("JustForTest"),
            account=gen_fake().phone_number(),
            email=gen_fake().email(),
            gender=gen_fake().random_element(enums.GenderEnum.values),
            real_name=gen_fake().name(),
            id_number=gen_fake().ssn(),
            born_date=gen_fake().date_of_birth(minimum_age=18, maximum_age=60),
            last_login_at=None,
            status=status,
            is_staff=is_staff,
            is_super_admin=is_super_admin,
            is_company_super_admin=is_company_super_admin,
            company=company,
        )
