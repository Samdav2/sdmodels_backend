# 📧 SDModels Email System - Quick Reference

## Overview
Complete email notification system with 25 professional templates covering all platform events.

## 🚀 Quick Start

### 1. Configure SMTP
Add to `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@sdmodels.com
EMAILS_FROM_NAME=SDModels
FRONTEND_URL=http://localhost:3000
```

### 2. Test Email System
```bash
python test_email_system.py
```

### 3. Send Test Email
```python
import asyncio
from app.utils.email import send_welcome_email

asyncio.run(send_welcome_email(
    user_email="test@example.com",
    username="TestUser",
    verify_url="http://localhost:3000/verify/abc123"
))
```

## 📋 All 25 Email Types

### Authentication (3)
1. **Welcome** - New user registration
2. **Password Reset** - Password recovery
3. **Email Verification** - Verify email address

### Models (3)
4. **Model Approved** - Model approved by admin
5. **Model Rejected** - Model rejected with reason
6. **Model Comment** - New comment on model

### Commerce (2)
7. **Purchase Confirmation** - Successful purchase
8. **New Sale** - Creator earned from sale

### Wallet (2)
9. **Deposit Confirmed** - Funds added to wallet
10. **Withdrawal Processed** - Funds withdrawn

### Bounties (8)
11. **Application Received** - New bounty application
12. **Application Approved** - Application accepted
13. **Application Rejected** - Application declined
14. **Submission Received** - Work submitted
15. **Submission Approved** - Work accepted, payment released
16. **Revision Requested** - Changes needed
17. **Bounty Cancelled** - Bounty cancelled by poster
18. **Dispute Resolved** - Admin resolved dispute

### Support (2)
19. **Ticket Created** - New support ticket
20. **Ticket Reply** - Agent replied to ticket

### Community (3)
21. **Community Invite** - Invited to community
22. **Community Approved** - Community approved by admin
23. **New Follower** - Someone followed you

### Moderation (2)
24. **Account Suspended** - Account suspended
25. **User Banned** - Restricted from activities

## 🔧 Usage Examples

### Send Welcome Email
```python
from app.utils.email import send_welcome_email

await send_welcome_email(
    user_email="user@example.com",
    username="JohnDoe",
    verify_url="https://sdmodels.com/verify/token123"
)
```

### Send Bounty Cancelled Email
```python
from app.utils.email import send_bounty_cancelled_email

await send_bounty_cancelled_email(
    user_email="artist@example.com",
    username="ArtistName",
    bounty_title="3D Character Model",
    cancellation_reason="Project requirements changed",
    bounties_url="https://sdmodels.com/bounties"
)
```

### Send Dispute Resolved Email
```python
from app.utils.email import send_dispute_resolved_email

await send_dispute_resolved_email(
    user_email="user@example.com",
    username="UserName",
    bounty_title="Logo Design",
    resolution_decision="Resolved in favor of: artist",
    resolution_notes="Work met all requirements",
    bounty_url="https://sdmodels.com/bounties/123"
)
```

## 📁 File Structure

```
app/
├── templates/
│   └── emails/
│       ├── welcome.html
│       ├── password_reset.html
│       ├── email_verification.html
│       ├── model_approved.html
│       ├── model_rejected.html
│       ├── model_comment.html
│       ├── purchase_confirmation.html
│       ├── new_sale.html
│       ├── wallet_deposit_confirmed.html
│       ├── wallet_withdrawal_processed.html
│       ├── bounty_application_received.html
│       ├── bounty_application_approved.html
│       ├── application_rejected.html
│       ├── bounty_submission_received.html
│       ├── bounty_submission_approved.html
│       ├── bounty_revision_requested.html
│       ├── bounty_cancelled.html
│       ├── support_ticket_created.html
│       ├── support_ticket_reply.html
│       ├── community_invite.html
│       ├── community_approved.html
│       ├── new_follower.html
│       ├── account_suspended.html
│       ├── user_banned.html
│       └── dispute_resolved.html
└── utils/
    └── email.py (26 email functions)
```

## 🎨 Template Design

All templates feature:
- Dark theme (#1a1a1a background)
- Red gradient branding (#dc2626 to #991b1b)
- Mobile-responsive layout
- Clear call-to-action buttons
- Professional typography
- Social links footer

## 🔒 Error Handling

All integrations use try-except blocks:
```python
try:
    await send_email_function(...)
except Exception as e:
    print(f"Failed to send email: {e}")
```

This ensures email failures don't block operations.

## 📊 Integration Points

| Email | File | Method/Endpoint |
|-------|------|-----------------|
| Welcome | `auth_service.py` | `register()` |
| Password Reset | `auth_service.py` | `request_password_reset()` |
| Email Verification | `auth_service.py` | `register()` |
| Model Approved | `admin.py` | `approve_model()` |
| Model Rejected | `admin.py` | `reject_model()` |
| Model Comment | `model_service.py` | `add_comment()` |
| Purchase Confirmation | `checkout.py` | `process_checkout()` |
| New Sale | `checkout.py` | `process_checkout()` |
| Wallet Deposit | `wallet_service.py` | `process_deposit()` |
| Wallet Withdrawal | `wallet_service.py` | `process_withdrawal()` |
| Application Received | `bounty_service.py` | `apply_to_bounty()` |
| Application Approved | `bounty_service.py` | `approve_application()` |
| Application Rejected | `bounty_service.py` | `reject_application()` |
| Submission Received | `bounty_service.py` | `submit_work()` |
| Submission Approved | `bounty_service.py` | `approve_submission()` |
| Revision Requested | `bounty_service.py` | `request_revision()` |
| Bounty Cancelled | `bounty_service.py` | `cancel_bounty()` |
| Ticket Created | `support.py` | `create_ticket()` |
| Ticket Reply | `support.py` | `reply_to_ticket()` |
| Community Invite | `community_service.py` | `invite_member()` |
| Community Approved | `admin.py` | `approve_community()` |
| New Follower | `users.py` | `follow_user()` |
| Account Suspended | `admin.py` | `suspend_user()` |
| User Banned | `bounty_admin_service.py` | `ban_user()` |
| Dispute Resolved | `bounty_admin_service.py` | `resolve_dispute()` |

## 🧪 Testing

### Test All Emails
```bash
python test_email_system.py
```

### Test Individual Email
```bash
python -c "
import asyncio
from app.utils.email import send_welcome_email

asyncio.run(send_welcome_email(
    'test@example.com',
    'TestUser',
    'http://localhost:3000/verify/123'
))
"
```

## 🐛 Troubleshooting

### Email Not Sending
1. Check SMTP credentials in `.env`
2. Verify SMTP server allows connections
3. Check firewall/port 587 access
4. Review application logs for errors

### Email in Spam
1. Configure SPF records
2. Set up DKIM signing
3. Add DMARC policy
4. Use reputable SMTP provider

### Template Not Rendering
1. Verify template file exists
2. Check template syntax
3. Ensure all variables passed
4. Test with simple template first

## 📈 Best Practices

1. **Always use try-except** - Don't let email failures block operations
2. **Use async functions** - Keep email sending non-blocking
3. **Test before production** - Verify all emails render correctly
4. **Monitor delivery rates** - Track bounces and spam reports
5. **Respect user preferences** - Allow email opt-out
6. **Keep templates updated** - Match current branding
7. **Use dynamic URLs** - Support multiple environments

## 🔐 Security

- Never log email content with sensitive data
- Use environment variables for SMTP credentials
- Implement rate limiting for email sending
- Validate email addresses before sending
- Use TLS for SMTP connections

## 📞 Support

For issues:
1. Check `.env` configuration
2. Review email logs
3. Test with `test_email_system.py`
4. Verify templates render
5. Check spam folder

## ✅ Status

- **Templates**: 25/25 ✅
- **Functions**: 26/26 ✅
- **Integrations**: 25/25 ✅
- **Production Ready**: YES ✅

---

**Last Updated**: 2026-03-02
**Version**: 1.0.0
**Status**: Production Ready
