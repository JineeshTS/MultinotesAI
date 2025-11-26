# Billing Guide

Everything you need to know about subscriptions, payments, tokens, and billing in MultinotesAI.

## Table of Contents

1. [Subscription Tiers](#subscription-tiers)
2. [Understanding Token Usage](#understanding-token-usage)
3. [Payment Methods](#payment-methods)
4. [Managing Your Subscription](#managing-your-subscription)
5. [Invoices and Receipts](#invoices-and-receipts)
6. [Upgrading and Downgrading](#upgrading-and-downgrading)
7. [Coupon Codes](#coupon-codes)
8. [Refund Policy](#refund-policy)
9. [Cancellation Policy](#cancellation-policy)
10. [Billing FAQ](#billing-faq)

---

## Subscription Tiers

MultinotesAI offers flexible subscription plans to match your needs and budget.

### Free Trial

**When you sign up, you get:**
- **Duration:** 7 days (or until trial tokens are used)
- **Text Tokens:** 5,000 tokens
- **File Tokens:** 1,000 tokens
- **Storage:** 1 GB
- **Features:** Full access to all AI models
- **Support:** Email support

**Perfect for:**
- Testing the platform
- Exploring features
- Small projects
- Proof of concept

**Limitations:**
- Limited token allowance
- Basic storage
- No priority processing

[Screenshot: Trial subscription badge]

---

### Basic Plan

**Price:** $9.99/month

**Includes:**
- **Text Tokens:** 50,000 per month
- **File Tokens:** 10,000 per month
- **Storage:** 5 GB
- **AI Models:** All models included
- **Support:** Priority email support
- **Validity:** 30 days

**Key Features:**
- ✅ Access to Together AI, Gemini, and OpenAI
- ✅ Unlimited documents
- ✅ Folder organization
- ✅ Content sharing
- ✅ Basic analytics
- ✅ Mobile access

**Best For:**
- Individual users
- Content creators
- Students and educators
- Small business owners
- Casual AI users

**What You Can Do:**
- Generate ~65,000 words of text per month
- Create ~50 AI images
- Transcribe ~10 hours of audio
- Analyze ~100 images

[Screenshot: Basic plan card]

---

### Pro Plan

**Price:** $24.99/month

**Includes:**
- **Text Tokens:** 150,000 per month
- **File Tokens:** 30,000 per month
- **Storage:** 20 GB
- **AI Models:** All models + priority access
- **Support:** Priority chat + email support
- **Validity:** 30 days

**Key Features:**
- ✅ Everything in Basic
- ✅ Priority AI processing (faster responses)
- ✅ Advanced analytics and insights
- ✅ Extended history (1 year retention)
- ✅ API access (coming soon)
- ✅ Custom templates
- ✅ Bulk operations
- ✅ Export capabilities

**Best For:**
- Professional content creators
- Marketing teams
- Agencies
- Developers
- Power users
- Regular AI usage

**What You Can Do:**
- Generate ~195,000 words of text per month
- Create ~150 AI images
- Transcribe ~30 hours of audio
- Analyze ~300 images
- Handle multiple client projects

[Screenshot: Pro plan card]

---

### Enterprise Plan

**Price:** Custom pricing (contact sales)

**Includes:**
- **Text Tokens:** Unlimited shared pool
- **File Tokens:** Unlimited shared pool
- **Storage:** Custom quota
- **AI Models:** All models + dedicated resources
- **Support:** Dedicated account manager + 24/7 support
- **Validity:** Flexible (annual contracts available)

**Key Features:**
- ✅ Everything in Pro
- ✅ Team collaboration tools
- ✅ Centralized billing
- ✅ User management dashboard
- ✅ Domain-based auto-assignment
- ✅ Usage analytics by user
- ✅ SSO integration (SAML, OAuth)
- ✅ Custom integrations
- ✅ SLA guarantees
- ✅ Data residency options
- ✅ Audit logs and compliance
- ✅ Custom workflows
- ✅ White-label options

**Best For:**
- Large organizations
- Enterprises with 10+ users
- Agencies with multiple teams
- Companies requiring compliance
- Organizations needing centralized control

**Billing:**
- Annual or multi-year contracts
- Monthly invoicing
- PO support
- Custom payment terms

[Screenshot: Enterprise plan features]

---

### Plan Comparison

| Feature | Trial | Basic | Pro | Enterprise |
|---------|:-----:|:-----:|:---:|:----------:|
| **Price** | Free | $9.99/mo | $24.99/mo | Custom |
| **Text Tokens** | 5K | 50K | 150K | Unlimited |
| **File Tokens** | 1K | 10K | 30K | Unlimited |
| **Storage** | 1 GB | 5 GB | 20 GB | Custom |
| **AI Models** | All | All | All | All |
| **Priority Processing** | ✗ | ✗ | ✓ | ✓ |
| **Email Support** | ✓ | ✓ | ✓ | ✓ |
| **Chat Support** | ✗ | ✗ | ✓ | ✓ |
| **Phone Support** | ✗ | ✗ | ✗ | ✓ |
| **API Access** | ✗ | ✗ | ✓ | ✓ |
| **Analytics** | Basic | Basic | Advanced | Enterprise |
| **Team Features** | ✗ | ✗ | ✗ | ✓ |
| **SSO** | ✗ | ✗ | ✗ | ✓ |
| **Dedicated Manager** | ✗ | ✗ | ✗ | ✓ |

[Screenshot: Detailed comparison table]

---

## Understanding Token Usage

Learn how tokens work and how to manage your usage effectively.

### What Are Tokens?

**Tokens are units of measurement** for AI processing:
- Represent chunks of text processed by AI models
- ~1 token = 4 characters or 0.75 words
- Both input (your prompt) and output (AI response) consume tokens

### Token Types

#### Text Tokens
Used for text-based operations:
- Text-to-text generation
- Code generation
- Conversations
- Text-only analysis

#### File Tokens
Used for file-based operations:
- Image generation and analysis
- Audio processing (speech-to-text, text-to-speech)
- Video analysis
- Document processing

**Why separate?** File operations require more computational resources, so they're tracked separately.

### Token Consumption Examples

#### Text Generation

| Task | Approximate Tokens |
|------|-------------------|
| Short email (100 words) | ~130 tokens |
| Blog introduction (250 words) | ~330 tokens |
| Full article (1000 words) | ~1,300 tokens |
| Long-form content (5000 words) | ~6,500 tokens |
| Code function (50 lines) | ~400 tokens |
| Complex script (200 lines) | ~1,600 tokens |

**Example Calculation:**
```
Prompt: "Write a 500-word article about SEO" (10 words)
Input tokens: ~13
Output tokens: ~650 (for 500 words)
Total: ~663 tokens
```

[Screenshot: Token usage calculator]

#### Image Operations

| Task | File Tokens |
|------|-------------|
| Generate image (standard quality) | 500-800 |
| Generate image (high quality) | 1,000-1,500 |
| Analyze uploaded image | 200-500 |
| Multiple images in one request | 500+ each |

#### Audio Operations

| Task | File Tokens (per minute) |
|------|--------------------------|
| Text-to-speech | ~300-500 |
| Speech-to-text (transcription) | ~400-600 |
| Audio analysis | ~500-700 |

#### Video Operations

| Task | File Tokens (per minute) |
|------|--------------------------|
| Video analysis | 1,000-2,000 |
| Video summarization | 1,500-2,500 |
| Complex video processing | 2,500+ |

### Monitoring Token Usage

#### Real-Time Balance

Your token balance is always visible:
- Top right corner of dashboard
- Shows remaining text tokens
- Shows remaining file tokens
- Click for detailed breakdown

[Screenshot: Token balance display]

#### Usage Dashboard

Access detailed usage information:
1. Click on your token balance
2. View usage dashboard with:
   - Current balance
   - Usage today/this week/this month
   - Usage by AI model
   - Usage by feature
   - Historical usage graph
   - Projected usage (based on trends)

[Screenshot: Token usage dashboard]

#### Usage Alerts

Get notified when tokens are running low:
- Alert at 75% usage
- Alert at 90% usage
- Alert at 100% usage
- Customize alert thresholds in Settings

**Alert Methods:**
- In-app notifications
- Email notifications
- Push notifications (mobile)

### Token Conservation Tips

**1. Be Concise with Prompts**
- Shorter prompts use fewer tokens
- Be specific but brief
- Remove unnecessary context

❌ **Bad:** "I need you to write me a professional business email that I can send to my client about the project that we discussed last week in our meeting where we talked about the timeline and deliverables..." (35 words = ~45 tokens)

✅ **Good:** "Write a professional email to a client about project timeline and deliverables." (12 words = ~16 tokens)

**2. Set Reasonable Output Lengths**
- Specify word count in your prompt
- Don't generate 2000 words if you need 500
- Use "write a brief..." or "write a detailed..."

**3. Use Appropriate Models**
- Some models are more token-efficient
- Together AI generally uses fewer tokens than OpenAI
- Choose based on quality needs vs. token cost

**4. Avoid Regenerating Unnecessarily**
- Review output carefully before regenerating
- Edit AI output instead of regenerating
- Save good outputs as templates

**5. Use Chatbot Mode Wisely**
- Chatbot mode keeps conversation history
- Each follow-up includes previous context
- Longer conversations use more tokens
- Start fresh conversation when changing topics

**6. Batch Similar Requests**
- Generate multiple items in one request
- "Write 3 product descriptions..." instead of 3 separate generations
- More efficient token usage

### Token Expiration

**Important:** Tokens expire at the end of your subscription period.

**Example:**
```
Subscription: Pro Plan ($24.99/month)
Start date: January 1
Tokens: 150,000 text + 30,000 file
Expiration: January 31

Used by Jan 31: 100,000 text + 20,000 file
Remaining: 50,000 text + 10,000 file
→ These 60,000 tokens expire on Jan 31

New period (Feb 1): Fresh 150,000 text + 30,000 file tokens
```

**Tokens DO NOT roll over to the next month.**

**Strategy:** Monitor usage toward the end of your billing cycle to maximize value.

---

## Payment Methods

MultinotesAI uses Razorpay for secure payment processing.

### Accepted Payment Methods

All payments are processed through Razorpay's secure platform.

#### Credit/Debit Cards
- ✅ Visa
- ✅ Mastercard
- ✅ American Express
- ✅ Discover
- ✅ Rupay (India)

**Card Requirements:**
- Valid expiration date
- CVV security code
- Billing address

[Screenshot: Card payment interface]

#### UPI (Unified Payments Interface)
- ✅ Google Pay
- ✅ PhonePe
- ✅ Paytm
- ✅ BHIM
- ✅ Any UPI app

**Available in:** India

[Screenshot: UPI payment options]

#### Net Banking
- ✅ All major Indian banks
- ✅ Instant bank transfer
- ✅ Direct debit

**Available in:** India

#### Digital Wallets
- ✅ Paytm
- ✅ PhonePe
- ✅ Mobikwik
- ✅ Airtel Money
- ✅ FreeCharge

**Available in:** India

#### EMI (Equated Monthly Installments)
- Available for purchases above ₹3,000
- 3, 6, 9, or 12-month options
- Selected banks only
- Additional interest may apply

[Screenshot: EMI options]

### Payment Security

**Your Payment Information is Safe:**
- 🔒 PCI DSS Level 1 Compliant
- 🔒 256-bit SSL encryption
- 🔒 No card details stored on our servers
- 🔒 Razorpay's secure infrastructure
- 🔒 Two-factor authentication
- 🔒 Fraud detection systems

**We NEVER see your:**
- Full card number
- CVV code
- Bank passwords
- UPI PIN

### Saved Payment Methods

**For Convenience:**
- Save payment methods in Razorpay
- Faster checkout on renewals
- Manage saved cards in settings
- Remove saved methods anytime

**To Save a Payment Method:**
1. During checkout, check "Save for future use"
2. Complete payment
3. Method is securely saved

**To Manage Saved Methods:**
1. Go to Settings → Billing → Payment Methods
2. View all saved methods
3. Set default payment method
4. Remove methods you no longer use

[Screenshot: Saved payment methods]

### Payment Currency

**Default Currency:** Based on your location
- USD (United States)
- INR (India)
- EUR (Europe)
- GBP (United Kingdom)

**Currency Conversion:**
- Handled automatically by payment processor
- Exchange rates updated daily
- Your bank may charge foreign transaction fees

---

## Managing Your Subscription

### Viewing Subscription Details

**Access Your Subscription:**
1. Click your profile icon (top right)
2. Select "Subscription" or "Billing"
3. View current subscription details

**Information Displayed:**
- Current plan name
- Monthly/annual billing
- Next billing date
- Token balance
- Storage usage
- Payment method
- Billing history

[Screenshot: Subscription details page]

### Automatic Renewal

**How It Works:**
- Subscriptions auto-renew by default
- Charged on renewal date
- Uses saved payment method
- Receive email confirmation
- New tokens allocated immediately

**Renewal Timeline:**
```
Day 1: Subscription starts
Day 30: Auto-renewal
  ├─ Payment processed
  ├─ New tokens allocated
  ├─ Confirmation email sent
  └─ Next renewal date set
```

### Managing Auto-Renewal

**To Disable Auto-Renewal:**
1. Go to Subscription settings
2. Find "Auto-Renewal" section
3. Toggle "Auto-Renew" to OFF
4. Confirm your choice

**What Happens:**
- Subscription continues until current period ends
- No charge on renewal date
- Account moves to free tier after expiration
- Data is preserved
- Can reactivate anytime

**To Re-Enable Auto-Renewal:**
1. Go to Subscription settings
2. Toggle "Auto-Renew" to ON
3. Verify payment method
4. Save changes

[Screenshot: Auto-renewal toggle]

### Updating Payment Method

**Change Your Payment Method:**
1. Go to Settings → Billing → Payment Methods
2. Click "Add Payment Method"
3. Enter new payment details
4. Set as default (if desired)
5. Save

**Or Update Existing:**
1. Find the saved payment method
2. Click "Update"
3. Enter new details
4. Save changes

**For Next Renewal:**
- New payment method is charged
- Old method can be removed
- Backup methods recommended

### Updating Billing Information

**Change Billing Details:**
1. Go to Settings → Billing → Billing Information
2. Update:
   - Name
   - Email (for invoices)
   - Company name
   - Tax ID / GST number
   - Billing address
3. Click "Save Changes"

**Important for:**
- Accurate invoices
- Tax compliance
- Company records
- Receipt delivery

[Screenshot: Billing information form]

---

## Invoices and Receipts

### Accessing Invoices

**View Your Invoices:**
1. Go to Settings → Billing → Invoices
2. See all past invoices
3. Filter by date range
4. Search by invoice number

[Screenshot: Invoice list]

**Invoice Details:**
- Invoice number
- Date issued
- Billing period
- Plan name
- Amount paid
- Payment method
- Tax details (if applicable)
- Company information

### Downloading Invoices

**To Download:**
1. Find the invoice in your list
2. Click "Download PDF"
3. Save to your device

**PDF Includes:**
- Professional invoice format
- All billing details
- Payment confirmation
- Tax breakdown
- Company letterhead

[Screenshot: Sample invoice PDF]

### Email Receipts

**Automatic Receipts:**
- Sent immediately after payment
- Sent to billing email address
- Includes payment confirmation
- Includes receipt/invoice

**Didn't Receive Receipt?**
1. Check spam/junk folder
2. Verify billing email is correct
3. Request resend from Billing page
4. Contact support if still missing

### Tax Invoices

**For Tax Purposes:**
- All invoices include applicable taxes
- GST invoices for Indian customers
- VAT invoices for EU customers
- Tax-compliant formatting
- Includes tax identification numbers

**Required Information:**
- Ensure GST/Tax ID is added to billing info
- Update company name for business invoices
- Keep billing address current
- Specify tax category if applicable

### Transaction History

**View All Transactions:**
1. Go to Settings → Billing → Transaction History
2. See complete payment history:
   - Date and time
   - Transaction ID
   - Amount
   - Status (success/failed/pending)
   - Payment method
   - Plan purchased

**Export Transactions:**
- Export to CSV for accounting
- Filter by date range
- Include all details
- Use for expense reports

[Screenshot: Transaction history]

---

## Upgrading and Downgrading

### Upgrading Your Plan

**Upgrade Anytime:**
1. Go to Subscription settings
2. Click "Upgrade Plan"
3. Select higher tier (Pro or Enterprise)
4. Review changes
5. Confirm upgrade

**What Happens When You Upgrade:**

**Immediate Effects:**
- ✅ New token allocation added immediately
- ✅ Storage limit increased
- ✅ Premium features unlocked
- ✅ Priority access enabled

**Billing:**
- Prorated charge for remaining days
- New plan starts immediately
- Next renewal at new price

**Example:**
```
Current: Basic ($9.99/mo)
Upgrade to: Pro ($24.99/mo)
Upgrade on: Day 15 of 30

Calculation:
- 15 days remaining on Basic
- Unused value: $9.99 × (15/30) = $4.99
- Pro cost for 15 days: $24.99 × (15/30) = $12.49
- Charge today: $12.49 - $4.99 = $7.50

Next renewal (Day 30): Full $24.99
```

**Tokens After Upgrade:**
- Keep remaining tokens from previous plan
- Add new plan's tokens
- Example: 10K left + 150K new = 160K total

[Screenshot: Upgrade confirmation]

### Downgrading Your Plan

**Downgrade Process:**
1. Go to Subscription settings
2. Click "Change Plan"
3. Select lower tier
4. Review what changes
5. Confirm downgrade

**What Happens When You Downgrade:**

**Timing:**
- ⏱️ Downgrade takes effect at end of current billing period
- Continue enjoying current plan until then
- No immediate changes
- No refund for current period

**At Next Renewal:**
- Lower token allocation
- Reduced storage limit
- May lose premium features

**Example:**
```
Current: Pro ($24.99/mo)
Downgrade to: Basic ($9.99/mo)
Downgrade requested: Day 15 of 30

Effect:
- Day 15-30: Still on Pro plan
- Day 30: Switched to Basic
- Next charge: $9.99 (Basic rate)
```

**Important Considerations:**

**Storage:**
- If you're using more than lower plan's limit
- Must reduce storage before downgrade
- Or pay for additional storage
- Downloaded files not affected

**Tokens:**
- Excess tokens are forfeited
- Use tokens before downgrade
- Or they expire at end of period

**Features:**
- May lose access to premium features
- Export data you need before downgrade
- API access may be revoked

[Screenshot: Downgrade warning]

### Switching Billing Frequency

**Change from Monthly to Annual:**
1. Go to Subscription settings
2. Select "Annual Billing"
3. Get 2 months free (discount)
4. Charged annually instead of monthly

**Annual Billing Benefits:**
- 💰 Save 16% compared to monthly
- 💰 2 months free with annual
- 📊 Consistent annual budgeting
- 🎁 Bonus tokens (in some plans)

**Example:**
```
Basic Plan:
Monthly: $9.99 × 12 = $119.88/year
Annual: $99.99/year
Savings: $19.89 (16% off)

Pro Plan:
Monthly: $24.99 × 12 = $299.88/year
Annual: $249.99/year
Savings: $49.89 (16% off)
```

**Change from Annual to Monthly:**
- Takes effect after annual period ends
- No refund for remaining annual period
- Can switch at renewal time

---

## Coupon Codes

Save money with promotional codes and special offers.

### How to Use Coupons

**Apply a Coupon:**
1. Select your plan
2. At checkout, find "Coupon Code" field
3. Enter your code
4. Click "Apply"
5. Discount is applied to total
6. Complete purchase

[Screenshot: Coupon code field at checkout]

### Types of Coupons

#### Percentage Discounts
```
Example: SAVE20
- 20% off your purchase
- Applies to plan price
- May have minimum order amount
```

#### Fixed Amount Discounts
```
Example: GET10
- $10 off your purchase
- Deducted from total
- May have minimum order amount
```

#### Bonus Tokens
```
Example: BONUS5K
- 5,000 extra tokens
- Added to your subscription
- Free bonus on top of plan
```

#### First-Time User Discounts
```
Example: FIRST50
- 50% off first month
- New users only
- One-time use
```

### Where to Find Coupons

**Official Sources:**
- Promotional emails
- Social media (Twitter, LinkedIn, Facebook)
- Referral program
- Special events and holidays
- Newsletter signup bonus
- Partner promotions

**Referral Rewards:**
- Get your referral code in Settings
- Share with friends
- They get discount
- You get bonus tokens when they subscribe

### Coupon Terms and Conditions

**Typical Restrictions:**
- One coupon per transaction
- Cannot combine with other offers
- May have expiration dates
- Minimum purchase amount may apply
- First-time user only (some coupons)
- Specific plans only (some coupons)

**Check Coupon Details:**
- Validity period
- Applicable plans
- Discount amount
- Minimum order value
- Maximum discount cap
- Usage limits

[Screenshot: Coupon details modal]

### Current Promotions

**Check for Active Offers:**
1. Go to Subscription page
2. Look for banner at top
3. View "Current Promotions"
4. See all active discounts

**Sign up for notifications:**
- Email alerts for new promos
- Push notifications for flash sales
- SMS alerts (opt-in)

---

## Refund Policy

### Refund Eligibility

**You may request a refund if:**
- ✅ Service is unavailable for extended periods
- ✅ Charged incorrectly due to system error
- ✅ Duplicate charges
- ✅ Charged after cancellation

**Refunds NOT available for:**
- ❌ Change of mind
- ❌ Tokens already used
- ❌ Partial month refunds (after usage)
- ❌ Annual subscriptions (after 14 days)

### Refund Request Process

**To Request a Refund:**
1. Go to Settings → Billing → Refund Request
2. Select transaction to refund
3. Provide reason
4. Submit request

**Or Contact Support:**
- Email: billing@multinotesai.com
- Include:
  - Transaction ID
  - Date of charge
  - Reason for refund
  - Account email

**Processing Time:**
- Request reviewed within 2 business days
- Approved refunds processed within 5-7 business days
- Refund to original payment method
- Email confirmation sent

[Screenshot: Refund request form]

### 14-Day Money-Back Guarantee

**For Annual Subscriptions:**
- Full refund if requested within 14 days
- Applies to annual plans only
- Must not have exceeded trial-level usage
- Account must not have violations

**How to Claim:**
1. Request refund within 14 days of purchase
2. Account is reviewed
3. Refund approved if eligible
4. Processed within 7 business days

### Partial Refunds

**Generally NOT Offered:**
- No pro-rated refunds for unused portion
- Tokens do not have cash value
- Cancellation does not trigger automatic refund

**Exception:**
- System errors resulting in service interruption
- Evaluated case-by-case by support team

---

## Cancellation Policy

### How to Cancel Your Subscription

**Cancel Anytime:**
1. Go to Settings → Subscription
2. Click "Cancel Subscription"
3. Select cancellation reason (optional feedback)
4. Confirm cancellation
5. Receive confirmation email

[Screenshot: Cancellation flow]

**Cancellation is Immediate in Effect:**
- ⚠️ Cancellation processes immediately
- ⚠️ No more charges on renewal date
- ⚠️ Access continues until period end
- ⚠️ Cannot undo (must resubscribe)

### What Happens After Cancellation

**Until End of Billing Period:**
- ✅ Continue using all features
- ✅ Keep current token balance
- ✅ Access all your content
- ✅ Use remaining tokens

**After Billing Period Ends:**
- ⚠️ Account moved to Free tier
- ⚠️ No new tokens allocated
- ⚠️ Storage limit reduced
- ⚠️ Premium features disabled
- ✅ Content preserved (read-only)
- ✅ Can download all content

**Timeline Example:**
```
Cancel on: January 15
Current period ends: January 31

Jan 15 - Jan 31: Full access as paid user
Feb 1: Account becomes free tier
  - No new token allocation
  - Storage limit: 1 GB
  - Content preserved but read-only
  - Can reactivate anytime
```

### Reactivating After Cancellation

**Easy Reactivation:**
1. Go to Subscription page
2. Click "Reactivate Subscription"
3. Choose plan
4. Enter payment details
5. Immediate reactivation

**What's Restored:**
- All your content
- Previous organization
- Full feature access
- New token allocation
- Premium features

### Data Retention After Cancellation

**Your Data is Safe:**
- All content preserved indefinitely
- Can access in read-only mode
- Download anytime
- Delete account separately if desired

**Storage Limitations:**
- If over free tier limit (1 GB)
- Must reduce storage or upgrade
- Cannot add new content until under limit

### Cancellation vs. Account Deletion

**Cancellation:**
- Stops billing
- Keeps account active
- Data preserved
- Can reactivate easily

**Account Deletion:**
- Permanently removes account
- Deletes all data
- Cannot be recovered
- Separate process (Settings → Account → Delete)

---

## Billing FAQ

### General Questions

**Q: When am I charged?**
A: You're charged immediately when subscribing, then on the same date each month (or year for annual plans).

**Q: Can I change my plan anytime?**
A: Yes, upgrade anytime with immediate effect. Downgrades take effect at next renewal.

**Q: Do unused tokens roll over?**
A: No, tokens expire at the end of each billing period and do not roll over.

**Q: What if I exceed my token limit?**
A: AI generation stops when tokens are depleted. Upgrade or wait for next renewal.

**Q: Can I buy additional tokens?**
A: Not currently. Upgrade to a higher plan for more tokens.

**Q: What happens if my payment fails?**
A: You'll receive an email notification. Update payment method within 7 days to avoid service interruption.

**Q: Can I pause my subscription?**
A: No, but you can cancel and reactivate when needed. All data is preserved.

**Q: Do you offer student discounts?**
A: Yes! Email support@multinotesai.com with your student ID for a discount code.

**Q: Do you offer non-profit discounts?**
A: Yes! Contact sales@multinotesai.com with your non-profit documentation.

**Q: Is there a free plan?**
A: We offer a free trial. After that, paid plans start at $9.99/month.

### Token Questions

**Q: How do I check my token balance?**
A: Your balance is always visible in the top-right corner of your dashboard.

**Q: Why did I use more tokens than expected?**
A: Both input and output consume tokens. Longer prompts and responses use more tokens. Chatbot mode includes conversation history.

**Q: Can I see token usage per generation?**
A: Yes, each generation shows tokens used in the response details.

**Q: Do failed generations consume tokens?**
A: No, you're only charged for successful completions.

**Q: What uses more tokens - Together AI or OpenAI?**
A: Generally similar, but depends on the specific request. OpenAI may be slightly more token-efficient for complex tasks.

### Payment Questions

**Q: Is my payment information secure?**
A: Yes, all payments processed through PCI-compliant Razorpay. We never see your card details.

**Q: Can I pay with PayPal?**
A: Not currently. We accept cards, UPI, net banking, and wallets through Razorpay.

**Q: Do you accept wire transfers for Enterprise?**
A: Yes, contact sales@multinotesai.com for wire transfer arrangements.

**Q: What currency are prices in?**
A: USD by default, but displays in local currency based on your location.

**Q: Are there any hidden fees?**
A: No hidden fees. Price shown is the price you pay (plus applicable taxes).

**Q: Can I get an invoice for my company?**
A: Yes, all transactions include downloadable invoices. Add your company details in billing settings.

### Subscription Questions

**Q: Can I switch from monthly to annual?**
A: Yes, anytime. You'll receive a prorated credit and save 16% annually.

**Q: What if I need to cancel mid-month?**
A: You keep access until period end. No refund for unused time.

**Q: Can multiple people use one subscription?**
A: Basic and Pro are for individual use. Use Enterprise for team access.

**Q: What happens if I don't renew?**
A: Account moves to free tier. All data preserved but features limited.

**Q: Can I export my data before canceling?**
A: Yes, bulk download available in Settings → Export Data.

### Enterprise Questions

**Q: How many users can we have?**
A: Unlimited users in Enterprise plan.

**Q: How is the token pool shared?**
A: All team members draw from the same pool. Admins can view per-user usage.

**Q: Can we set limits per user?**
A: Yes, Enterprise admins can set token limits per user or team.

**Q: Do we get a dedicated account manager?**
A: Yes, all Enterprise customers get a dedicated account manager.

**Q: Can we get custom contract terms?**
A: Yes, contact sales@multinotesai.com for custom agreements.

**Q: Do you offer annual invoicing?**
A: Yes, annual billing available with payment terms negotiable.

---

## Getting Help with Billing

### Support Channels

**Email Support:**
- billing@multinotesai.com
- Response within 24 hours
- Include account email and transaction ID

**Live Chat:**
- Available in-app
- 9 AM - 6 PM IST, Monday-Friday
- Instant assistance

**Phone Support (Enterprise Only):**
- Dedicated hotline for Enterprise customers
- 24/7 availability
- Priority handling

### Billing Disputes

**If You Believe You Were Charged Incorrectly:**
1. Check transaction history
2. Review invoice details
3. Contact billing support with:
   - Transaction ID
   - Expected charge vs. actual charge
   - Screenshots if helpful
4. We'll investigate within 2 business days

### Payment Issues

**If Your Payment Fails:**
1. Check card/account balance
2. Verify card is not expired
3. Ensure correct billing details
4. Try alternate payment method
5. Contact your bank if issues persist
6. Contact our support if needed

### Resources

- **Billing Portal:** Settings → Billing
- **Help Center:** help.multinotesai.com/billing
- **Video Tutorials:** Watch step-by-step guides
- **Community Forum:** Ask questions and share experiences

---

**We're here to help with all your billing needs!**

**Contact Us:**
- Billing: billing@multinotesai.com
- Sales: sales@multinotesai.com
- Support: support@multinotesai.com
- Website: https://www.multinotesai.com

**Last Updated:** November 2025
