import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from app.core.config import settings

# Setup Jinja2 environment for email templates
template_dir = Path(__file__).parent.parent / "templates" / "emails"
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))


async def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    context: dict
):
    """Send email using SMTP"""
    
    # Render template
    template = jinja_env.get_template(template_name)
    html_content = template.render(**context)
    
    # Create message
    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    
    # Attach HTML content
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    # Send email
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=True
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


async def send_welcome_email(user_email: str, username: str, verify_url: str):
    """Send welcome email to new user"""
    return await send_email(
        to_email=user_email,
        subject="Welcome to SDModels! 🎉",
        template_name="welcome.html",
        context={
            "username": username,
            "verify_url": verify_url
        }
    )


async def send_password_reset_email(user_email: str, username: str, reset_url: str):
    """Send password reset email"""
    return await send_email(
        to_email=user_email,
        subject="Reset Your Password - SDModels",
        template_name="password_reset.html",
        context={
            "username": username,
            "reset_url": reset_url
        }
    )


async def send_model_approved_email(user_email: str, username: str, model_title: str, model_url: str):
    """Send model approval notification"""
    return await send_email(
        to_email=user_email,
        subject="Your Model is Live! 🚀",
        template_name="model_approved.html",
        context={
            "username": username,
            "model_title": model_title,
            "model_url": model_url
        }
    )


async def send_purchase_confirmation_email(
    user_email: str,
    username: str,
    transaction_id: str,
    items: list,
    total: float,
    download_url: str
):
    """Send purchase confirmation email"""
    return await send_email(
        to_email=user_email,
        subject="Purchase Confirmation - SDModels",
        template_name="purchase_confirmation.html",
        context={
            "username": username,
            "transaction_id": transaction_id,
            "items": items,
            "total": total,
            "download_url": download_url
        }
    )


async def send_new_sale_email(
    user_email: str,
    username: str,
    model_title: str,
    sale_price: float,
    platform_fee: float,
    your_earnings: float,
    transaction_id: str,
    dashboard_url: str
):
    """Send new sale notification to creator"""
    return await send_email(
        to_email=user_email,
        subject="You Made a Sale! 💰",
        template_name="new_sale.html",
        context={
            "username": username,
            "model_title": model_title,
            "sale_price": sale_price,
            "platform_fee": platform_fee,
            "your_earnings": your_earnings,
            "transaction_id": transaction_id,
            "dashboard_url": dashboard_url
        }
    )


# Wallet Email Functions
async def send_wallet_deposit_email(
    user_email: str,
    username: str,
    amount: float,
    transaction_id: str,
    payment_method: str,
    transaction_date: str,
    new_balance: float,
    wallet_url: str
):
    """Send wallet deposit confirmation email"""
    return await send_email(
        to_email=user_email,
        subject="Deposit Confirmed - SDModels",
        template_name="wallet_deposit_confirmed.html",
        context={
            "username": username,
            "amount": amount,
            "transaction_id": transaction_id,
            "payment_method": payment_method,
            "transaction_date": transaction_date,
            "new_balance": new_balance,
            "wallet_url": wallet_url
        }
    )


async def send_wallet_withdrawal_email(
    user_email: str,
    username: str,
    amount: float,
    transaction_id: str,
    withdrawal_method: str,
    transaction_date: str,
    remaining_balance: float
):
    """Send wallet withdrawal processed email"""
    return await send_email(
        to_email=user_email,
        subject="Withdrawal Processed - SDModels",
        template_name="wallet_withdrawal_processed.html",
        context={
            "username": username,
            "amount": amount,
            "transaction_id": transaction_id,
            "withdrawal_method": withdrawal_method,
            "transaction_date": transaction_date,
            "remaining_balance": remaining_balance
        }
    )


# Bounty Email Functions
async def send_bounty_application_received_email(
    user_email: str,
    username: str,
    bounty_title: str,
    applicant_username: str,
    proposed_timeline: str,
    application_date: str,
    bounty_url: str
):
    """Send email when someone applies to a bounty"""
    return await send_email(
        to_email=user_email,
        subject="New Bounty Application - SDModels",
        template_name="bounty_application_received.html",
        context={
            "username": username,
            "bounty_title": bounty_title,
            "applicant_username": applicant_username,
            "proposed_timeline": proposed_timeline,
            "application_date": application_date,
            "bounty_url": bounty_url
        }
    )


async def send_bounty_application_approved_email(
    user_email: str,
    username: str,
    bounty_title: str,
    bounty_amount: float,
    deadline: str,
    poster_username: str,
    bounty_url: str
):
    """Send email when bounty application is approved"""
    return await send_email(
        to_email=user_email,
        subject="Your Application Was Approved! - SDModels",
        template_name="bounty_application_approved.html",
        context={
            "username": username,
            "bounty_title": bounty_title,
            "bounty_amount": bounty_amount,
            "deadline": deadline,
            "poster_username": poster_username,
            "bounty_url": bounty_url
        }
    )


async def send_bounty_submission_received_email(
    user_email: str,
    username: str,
    bounty_title: str,
    creator_username: str,
    submission_date: str,
    bounty_amount: float,
    submission_url: str
):
    """Send email when bounty work is submitted"""
    return await send_email(
        to_email=user_email,
        subject="Bounty Submission Received - SDModels",
        template_name="bounty_submission_received.html",
        context={
            "username": username,
            "bounty_title": bounty_title,
            "creator_username": creator_username,
            "submission_date": submission_date,
            "bounty_amount": bounty_amount,
            "submission_url": submission_url
        }
    )


async def send_bounty_submission_approved_email(
    user_email: str,
    username: str,
    bounty_amount: float,
    wallet_url: str
):
    """Send email when bounty submission is approved and payment released"""
    return await send_email(
        to_email=user_email,
        subject="Bounty Completed! Payment Released - SDModels",
        template_name="bounty_submission_approved.html",
        context={
            "username": username,
            "bounty_amount": bounty_amount,
            "wallet_url": wallet_url
        }
    )


async def send_bounty_revision_requested_email(
    user_email: str,
    username: str,
    poster_username: str,
    feedback: str,
    bounty_url: str
):
    """Send email when revision is requested on bounty submission"""
    return await send_email(
        to_email=user_email,
        subject="Revision Requested - SDModels",
        template_name="bounty_revision_requested.html",
        context={
            "username": username,
            "poster_username": poster_username,
            "feedback": feedback,
            "bounty_url": bounty_url
        }
    )


# Support Email Functions
async def send_support_ticket_created_email(
    user_email: str,
    username: str,
    ticket_id: str,
    subject: str,
    priority: str,
    status: str,
    ticket_url: str
):
    """Send email when support ticket is created"""
    return await send_email(
        to_email=user_email,
        subject=f"Support Ticket Created - #{ticket_id}",
        template_name="support_ticket_created.html",
        context={
            "username": username,
            "ticket_id": ticket_id,
            "subject": subject,
            "priority": priority,
            "status": status,
            "ticket_url": ticket_url
        }
    )


async def send_support_ticket_reply_email(
    user_email: str,
    username: str,
    ticket_id: str,
    agent_name: str,
    message: str,
    ticket_url: str
):
    """Send email when support agent replies to ticket"""
    return await send_email(
        to_email=user_email,
        subject=f"New Reply on Ticket #{ticket_id}",
        template_name="support_ticket_reply.html",
        context={
            "username": username,
            "ticket_id": ticket_id,
            "agent_name": agent_name,
            "message": message,
            "ticket_url": ticket_url
        }
    )


# Model Email Functions
async def send_model_rejected_email(
    user_email: str,
    username: str,
    model_title: str,
    rejection_reason: str,
    model_url: str
):
    """Send email when model is rejected"""
    return await send_email(
        to_email=user_email,
        subject="Model Review Update - SDModels",
        template_name="model_rejected.html",
        context={
            "username": username,
            "model_title": model_title,
            "rejection_reason": rejection_reason,
            "model_url": model_url
        }
    )


# Community Email Functions
async def send_community_invite_email(
    user_email: str,
    username: str,
    inviter_username: str,
    community_name: str,
    community_description: str,
    member_count: int,
    community_url: str
):
    """Send email when user is invited to a community"""
    return await send_email(
        to_email=user_email,
        subject=f"You're Invited to {community_name}!",
        template_name="community_invite.html",
        context={
            "username": username,
            "inviter_username": inviter_username,
            "community_name": community_name,
            "community_description": community_description,
            "member_count": member_count,
            "community_url": community_url
        }
    )



# Additional Email Functions

async def send_email_verification_email(
    user_email: str,
    username: str,
    verify_url: str,
    verification_code: str
):
    """Send email verification"""
    return await send_email(
        to_email=user_email,
        subject="Verify Your Email - SDModels",
        template_name="email_verification.html",
        context={
            "username": username,
            "verify_url": verify_url,
            "verification_code": verification_code
        }
    )


async def send_new_follower_email(
    user_email: str,
    username: str,
    follower_username: str,
    follower_bio: str,
    follower_profile_url: str
):
    """Send new follower notification"""
    return await send_email(
        to_email=user_email,
        subject=f"{follower_username} started following you!",
        template_name="new_follower.html",
        context={
            "username": username,
            "follower_username": follower_username,
            "follower_bio": follower_bio or "No bio yet",
            "follower_profile_url": follower_profile_url
        }
    )


async def send_model_comment_email(
    user_email: str,
    username: str,
    commenter_username: str,
    model_title: str,
    comment_content: str,
    model_url: str
):
    """Send notification when someone comments on user's model"""
    return await send_email(
        to_email=user_email,
        subject=f"New comment on {model_title}",
        template_name="model_comment.html",
        context={
            "username": username,
            "commenter_username": commenter_username,
            "model_title": model_title,
            "comment_content": comment_content,
            "model_url": model_url
        }
    )


async def send_bounty_cancelled_email(
    user_email: str,
    username: str,
    bounty_title: str,
    cancellation_reason: str,
    bounties_url: str
):
    """Send email when bounty is cancelled"""
    return await send_email(
        to_email=user_email,
        subject=f"Bounty Cancelled: {bounty_title}",
        template_name="bounty_cancelled.html",
        context={
            "username": username,
            "bounty_title": bounty_title,
            "cancellation_reason": cancellation_reason,
            "bounties_url": bounties_url
        }
    )


async def send_application_rejected_email(
    user_email: str,
    username: str,
    bounty_title: str,
    bounties_url: str
):
    """Send email when bounty application is rejected"""
    return await send_email(
        to_email=user_email,
        subject="Application Update - SDModels",
        template_name="application_rejected.html",
        context={
            "username": username,
            "bounty_title": bounty_title,
            "bounties_url": bounties_url
        }
    )


async def send_account_suspended_email(
    user_email: str,
    username: str,
    suspension_reason: str,
    suspension_duration: str,
    appeal_url: str
):
    """Send email when account is suspended"""
    return await send_email(
        to_email=user_email,
        subject="Account Suspended - SDModels",
        template_name="account_suspended.html",
        context={
            "username": username,
            "suspension_reason": suspension_reason,
            "suspension_duration": suspension_duration,
            "appeal_url": appeal_url
        }
    )


async def send_user_banned_email(
    user_email: str,
    username: str,
    restriction_type: str,
    reason: str,
    duration: str,
    support_url: str
):
    """Send email when user is banned from specific activities"""
    return await send_email(
        to_email=user_email,
        subject="Account Restriction Notice - SDModels",
        template_name="user_banned.html",
        context={
            "username": username,
            "restriction_type": restriction_type,
            "reason": reason,
            "duration": duration,
            "support_url": support_url
        }
    )


async def send_dispute_resolved_email(
    user_email: str,
    username: str,
    bounty_title: str,
    resolution_decision: str,
    resolution_notes: str,
    bounty_url: str
):
    """Send email when dispute is resolved"""
    return await send_email(
        to_email=user_email,
        subject=f"Dispute Resolved: {bounty_title}",
        template_name="dispute_resolved.html",
        context={
            "username": username,
            "bounty_title": bounty_title,
            "resolution_decision": resolution_decision,
            "resolution_notes": resolution_notes,
            "bounty_url": bounty_url
        }
    )


async def send_community_approved_email(
    user_email: str,
    username: str,
    community_name: str,
    community_url: str
):
    """Send email when community is approved"""
    return await send_email(
        to_email=user_email,
        subject=f"Your Community is Live: {community_name}",
        template_name="community_approved.html",
        context={
            "username": username,
            "community_name": community_name,
            "community_url": community_url
        }
    )
