from typing import Any, Optional
from eden.components import Component, register, action
from eden.admin.models import SupportTicket, TicketMessage
from markupsafe import Markup

@register("support_ticket")
class SupportTicketComponent(Component):
    """
    User-facing support ticket component.
    Allows users to report issues directly from the frontend.
    """
    template_name = "support.html"

    def __init__(self, subject: str = "", message: str = "", submitted: bool = False, error: Optional[str] = None, **kwargs: Any):
        self.subject = subject
        self.message = message
        self.submitted = submitted
        self.error = error
        super().__init__(**kwargs)

    @action
    async def submit(self, request: Any, subject: str, message: str) -> Any:
        """Handle ticket submission."""
        if not subject or not message:
            self.error = "Please fill in all fields."
            return await self.render()

        try:
            user = getattr(request.state, "user", None)
            tenant_id = getattr(request.state, "tenant_id", None)
            
            # Create the ticket
            ticket = await SupportTicket.create(
                subject=subject,
                user_id=str(user.id) if user else None,
                tenant_id=str(tenant_id) if tenant_id else None,
                status="Open",
                priority="Medium"
            )
            
            # Create the initial message
            await TicketMessage.create(
                ticket_id=ticket.id,
                content=message,
                author_name=getattr(user, "name", "Anonymous User"),
                is_admin=False
            )
            
            self.submitted = True
            self.subject = ""
            self.message = ""
            self.error = None
        except Exception as e:
            self.error = f"Failed to submit ticket: {str(e)}"
            
        return await self.render()
