class BasePublisher:
    def __init__(self, integration):
        self.integration = integration
        self.access_token = integration.access_token
        self.account_id = integration.account_id

    def publish(self, post_text, image_url=None):
        raise NotImplementedError("Each platform must implement its own publish method.")
