# pyrefly: ignore [missing-import]
from django.test import TestCase
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
from core.models import Organization, PlatformIntegration
from core.publishers import get_publisher, BasePublisher, PUBLISHER_MAP
from unittest.mock import patch, MagicMock

class PublisherEngineTestCase(TestCase):
    def setUp(self):
        # Create user and organization for testing PlatformIntegration
        self.user = User.objects.create_user(username="testuser", password="password")
        self.org = Organization.objects.create(name="Test Org", owner=self.user)

    @patch('core.publishers.facebook.requests.post')
    @patch('core.publishers.instagram.requests.post')
    @patch('core.publishers.linkedin.requests.post')
    @patch('core.publishers.x_twitter.requests.post')
    @patch('core.publishers.threads.requests.post')
    @patch('core.publishers.pinterest.requests.post')
    @patch('core.publishers.youtube.requests.post')
    @patch('core.publishers.tiktok.requests.post')
    @patch('core.publishers.reddit.requests.post')
    @patch('core.publishers.blogger.requests.post')
    def test_factory_resolves_all_platforms(self, *mock_posts):
        """Test that the get_publisher factory resolves and instantiates correct subclasses for all supported platforms."""
        
        # Setup mock responses
        for mock_post in mock_posts:
            mock_response = MagicMock()
            mock_response.json.return_value = {"id": "mocked_id", "data": {"publish_id": "mocked_id"}}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

        for platform_code, platform_name in PlatformIntegration.PLATFORM_CHOICES:
            integration = PlatformIntegration.objects.create(
                organization=self.org,
                platform=platform_code,
                access_token=f"token_{platform_code}",
                account_id=f"id_{platform_code}",
                is_active=True
            )
            
            # Retrieve the publisher strategy using the updated signature
            publisher = get_publisher(integration.platform, integration)
            
            # Assertions
            self.assertIsInstance(publisher, BasePublisher)
            self.assertEqual(publisher.access_token, f"token_{platform_code}")
            self.assertEqual(publisher.account_id, f"id_{platform_code}")
            self.assertEqual(publisher.integration, integration)
            
            # Call publish (now using mocked requests)
            success, result_id = publisher.publish("Hello World", image_url="https://example.com/image.jpg")
            
            # If the platform requires an image and we didn't pass one, it might fail. But we passed one.
            # (Note: TikTok might require specific JSON structure, but our mocks will return a dict anyway)
            if not success:
                print(f"Failed on {platform_code}: {result_id}")
            self.assertTrue(success)
            
            # Clean up for next loop iteration (due to unique_together constraint)
            integration.delete()

    def test_factory_unsupported_platform_raises_error(self):
        """Test that passing an integration with an unsupported platform type raises ValueError."""
        # Force a platform check by mocking integration platform
        class MockIntegration:
            def __init__(self):
                self.platform = "unsupported_platform"
                self.access_token = "dummy_token"
                self.account_id = "dummy_id"
                
        integration = MockIntegration()
        with self.assertRaises(ValueError) as context:
            get_publisher(integration.platform, integration)
        self.assertIn("Unsupported platform", str(context.exception))
