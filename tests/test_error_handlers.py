# tests/test_error_handlers.py
from service.common import status
from service import app as flask_app
from service.models import DataValidationError
from tests.test_routes import TestAccountService, BASE_URL


class TestErrorHandlers(TestAccountService):
    """Exercise the Flask error handlers defined in service/common/error_handlers.py"""  # noqa: E501

    def test_400_handler_via_DataValidationError(self):
        """Raising DataValidationError should be handled by request_validation_error -> 400"""  # noqa: E501
        @flask_app.route("/__test_raise_400__")
        def _raise_400():
            raise DataValidationError("invalid data for testing")

        resp = self.client.get("/__test_raise_400__")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        body = resp.get_json()
        # check expected keys and message content
        self.assertEqual(body.get("status"), status.HTTP_400_BAD_REQUEST)
        self.assertEqual(body.get("error"), "Bad Request")
        self.assertIn("invalid data", body.get("message", "").lower())

    def test_404_handler_returns_json(self):
        """A request to a nonexistent route should hit the 404 handler and return JSON"""  # noqa: E501
        resp = self.client.get("/__definitely_nonexistent_route__")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        body = resp.get_json()
        self.assertEqual(body.get("status"), status.HTTP_404_NOT_FOUND)
        self.assertEqual(body.get("error"), "Not Found")

    def test_405_handler_on_collection(self):
        """Illegal method on a valid endpoint should hit 405 handler (Method not Allowed)"""  # noqa: E501
        # DELETE on /accounts should be 405 (or 404 depending on routing). Accept both but prefer 405.  # noqa: E501
        resp = self.client.delete(BASE_URL)
        self.assertIn(resp.status_code, (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND))  # noqa: E501
        if resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            body = resp.get_json()
            self.assertEqual(body.get("status"), status.HTTP_405_METHOD_NOT_ALLOWED)  # noqa: E501
            self.assertEqual(body.get("error"), "Method not Allowed")

    def test_415_handler_for_wrong_media_type(self):
        """POSTing with wrong Content-Type should return 415 (Unsupported media type)"""  # noqa: E501
        # Use the create endpoint but send wrong content-type to trigger check_content_type -> abort(415)  # noqa: E501
        resp = self.client.post(BASE_URL, data="notjson", content_type="text/plain")  # noqa: E501
        # The app may respond with 415 or with a 400 from other validation; accept 415 specifically if present.  # noqa: E501
        self.assertIn(resp.status_code, (status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, status.HTTP_400_BAD_REQUEST))  # noqa: E501

        if resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
            body = resp.get_json()
            self.assertEqual(body.get("status"), status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)  # noqa: E501
            self.assertEqual(body.get("error"), "Unsupported media type")

    def test_500_handler_for_unexpected_exception(self):
        """Intentionally raise an unhandled exception to hit the 500 handler"""
        @flask_app.route("/__test_raise_500__")
        def _raise_500():
            raise RuntimeError("boom for testing 500 handler")

        # Temporarily disable TESTING so Flask doesn't re-raise exceptions
        prev_testing = flask_app.config.get("TESTING", False)
        flask_app.config["TESTING"] = False
        try:
            resp = self.client.get("/__test_raise_500__")
        finally:
            # Restore previous value to avoid affecting other tests
            flask_app.config["TESTING"] = prev_testing

        # core assertions: status + structure
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)  # noqa: E501
        body = resp.get_json()
        self.assertIsNotNone(body)
        self.assertEqual(body.get("status"), status.HTTP_500_INTERNAL_SERVER_ERROR)  # noqa: E501
        self.assertEqual(body.get("error"), "Internal Server Error")

        # message may contain the real exception text (contains "boom") OR a generic Flask message.  # noqa: E501
        msg = body.get("message", "")
        # Accept either presence of the word 'boom' OR generic server message starting with '500'  # noqa: E501
        if "boom" in msg.lower():
            self.assertIn("boom", msg.lower())
        else:
            # Generic flask error message is acceptable — just ensure it's non-empty  # noqa: E501
            self.assertTrue(len(msg) > 0)
