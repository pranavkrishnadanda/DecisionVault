import pytest
from rest_framework.exceptions import NotAuthenticated

from core.permissions import get_user_membership_or_raise


@pytest.mark.django_db
class TestCorePermissionsModule:
    def test_anonymous_user_is_rejected(self):
        class AnonymousUser:
            is_authenticated = False

        with pytest.raises(NotAuthenticated):
            get_user_membership_or_raise(AnonymousUser())
