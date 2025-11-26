# Collaboration Guide

Learn how to share content, collaborate with team members, and manage privacy settings in MultinotesAI.

## Table of Contents

1. [Introduction to Collaboration](#introduction-to-collaboration)
2. [Sharing Documents](#sharing-documents)
3. [Sharing Folders](#sharing-folders)
4. [Sharing Files](#sharing-files)
5. [Access Permissions](#access-permissions)
6. [Managing Shared Content](#managing-shared-content)
7. [Team Collaboration Features](#team-collaboration-features)
8. [Enterprise Features](#enterprise-features)
9. [Privacy Settings](#privacy-settings)
10. [Best Practices](#best-practices)

---

## Introduction to Collaboration

MultinotesAI makes it easy to collaborate with team members, clients, or partners by sharing your AI-generated content.

### What Can You Share?

- **Documents** - AI-generated text, code, and content
- **Folders** - Entire folder structures with multiple items
- **Files** - Uploaded images, audio, video, and documents

### Who Can You Share With?

- **Individual Users** - Share with specific MultinotesAI users
- **Team Members** - Share within your organization (Enterprise)
- **External Collaborators** - Invite people to view specific content

### Collaboration Benefits

- **Real-time Access** - Shared content updates instantly
- **Version Control** - Track changes and see edit history
- **Controlled Permissions** - Decide who can view or edit
- **Centralized Storage** - Everyone accesses the same source
- **Audit Trail** - See who accessed what and when

[Screenshot: Collaboration overview dashboard]

---

## Sharing Documents

Share individual documents with others for viewing or editing.

### How to Share a Document

#### Method 1: From Document View

1. Open the document you want to share
2. Click the "Share" button (top right)
3. The Share dialog opens

[Screenshot: Share button on document]

#### Method 2: From Documents List

1. Right-click on the document
2. Select "Share" from the menu
3. The Share dialog opens

[Screenshot: Share option in context menu]

### Share Dialog

[Screenshot: Share dialog with all options]

**Step 1: Choose Recipient**
1. Enter email address or username
2. Search for existing MultinotesAI users
3. For non-users, they'll receive an invitation

**Step 2: Set Permissions**
- **Can View** - Read-only access
- **Can Edit** - Can modify the document

**Step 3: Add Message (Optional)**
- Include a personal message
- Explain why you're sharing
- Provide context or instructions

**Step 4: Additional Options**
- **Notify via email** - Send notification email (default: on)
- **Set expiration** - Access expires after date
- **Allow resharing** - Recipient can share with others

**Step 5: Share**
- Click "Share" to send
- Recipient receives notification
- Document appears in their "Shared with Me" section

### Document Sharing Example

**Scenario:** Sharing a blog post draft with a client for review

```
To: client@example.com
Permission: Can View (read-only)
Message: "Hi Sarah, here's the draft blog post we discussed.
Please review and let me know your thoughts by Friday.
Thanks!"
Expiration: 7 days from now
Notify via email: ✓ Yes
```

[Screenshot: Completed share dialog example]

### Managing Document Shares

**View Who Has Access:**
1. Open the document
2. Click "Share" button
3. See list of people with access
4. See their permission levels

**Modify Permissions:**
1. In the share list, click on a person
2. Change from "Can View" to "Can Edit" (or vice versa)
3. Changes take effect immediately

**Remove Access:**
1. In the share list, find the person
2. Click the "Remove" or "X" button
3. Confirm removal
4. They lose access immediately

[Screenshot: Manage shared users interface]

---

## Sharing Folders

Share entire folders to give access to multiple items at once.

### Why Share Folders?

- Share project folders with clients
- Collaborate on ongoing campaigns
- Provide access to resource libraries
- Organize team workspaces

### How to Share a Folder

1. Navigate to your folders list
2. Right-click on the folder to share
3. Select "Share Folder"
4. Follow the same process as document sharing

[Screenshot: Share folder dialog]

### Folder Sharing Behavior

**What Recipients See:**
- The folder appears in their "Shared with Me" section
- They see all current contents
- New items added to the folder automatically become accessible
- Subfolder structure is preserved

**Permission Inheritance:**
- Folder permission applies to all contents
- If folder is "Can Edit", all documents inside are editable
- If folder is "Can View", all contents are read-only
- Individual item permissions can override folder permissions

### Folder Sharing Example

**Scenario:** Sharing a client project folder

```
Folder: "ABC Corp - Website Content"
Contains:
├── Homepage Copy.doc
├── About Page.doc
├── Product Descriptions/
│   ├── Product A.doc
│   └── Product B.doc
└── Images/
    ├── hero-image.png
    └── logo.png

Shared with: client@abccorp.com
Permission: Can View
Message: "All your website content is here. Review and provide feedback."
```

When shared, the client sees the exact folder structure with all files.

[Screenshot: Shared folder view for recipient]

### Nested Folders and Sharing

**Sharing Parent Folders:**
- Shares all subfolders automatically
- Recipient gets access to entire hierarchy
- New subfolders added later are also shared

**Sharing Individual Subfolders:**
- You can share just a subfolder
- Parent folder remains private
- Recipient only sees that subfolder

### Managing Folder Shares

**Add More Recipients:**
1. Open share settings for the folder
2. Add new recipients
3. They get access to all contents

**Adjust Permissions:**
- Change view/edit permissions
- Applies to entire folder contents
- Updates instantly for all recipients

**Stop Sharing:**
1. Remove all recipients, OR
2. Click "Stop Sharing" to remove everyone at once

---

## Sharing Files

Share uploaded files (images, audio, video) with others.

### How to Share Files

Same process as documents:
1. Right-click on the file
2. Select "Share"
3. Choose recipients and permissions
4. Send

### File Sharing Use Cases

**Design Reviews:**
- Share image files with designers
- Get feedback on visuals
- Collaborate on revisions

**Audio Collaboration:**
- Share audio files with editors
- Provide voice-overs for review
- Collaborate on podcast content

**Video Projects:**
- Share video files for analysis
- Provide raw footage to team
- Review video content together

### File Size Considerations

- Large files may take time to load for recipients
- Recipients don't count file size against their storage quota
- Original uploader's storage is used
- Consider compressing very large files before sharing

[Screenshot: Share file dialog with size warning]

---

## Access Permissions

Understand the two permission levels available in MultinotesAI.

### Can View (Read-Only)

**Recipients Can:**
- ✅ Open and view the content
- ✅ Download their own copy
- ✅ See version history
- ✅ Add comments (if enabled)
- ✅ Print content

**Recipients Cannot:**
- ❌ Edit the original content
- ❌ Delete the content
- ❌ Rename files or documents
- ❌ Move content to different folders
- ❌ Share with others (unless "Allow resharing")

**Best For:**
- Client reviews
- Final deliverables
- Reference materials
- Read-only documentation
- Presentations and reports

[Screenshot: View-only interface for recipient]

### Can Edit

**Recipients Can:**
- ✅ Everything in "Can View"
- ✅ Edit the content
- ✅ Add new items to shared folders
- ✅ Rename items (in shared folders)
- ✅ Create new versions
- ✅ Restore previous versions

**Recipients Cannot:**
- ❌ Delete the original (only owner can)
- ❌ Change sharing settings
- ❌ Remove other collaborators
- ❌ Transfer ownership

**Best For:**
- Team collaboration
- Co-authoring documents
- Shared workspaces
- Active projects
- Content development

**Important:** Edits are saved to the original document. All collaborators see changes in real-time.

[Screenshot: Edit interface for collaborator]

### Permission Comparison Table

| Feature | Can View | Can Edit |
|---------|:--------:|:--------:|
| Open/Read | ✓ | ✓ |
| Download | ✓ | ✓ |
| Print | ✓ | ✓ |
| Comment | ✓ | ✓ |
| Version History | ✓ | ✓ |
| Edit Content | ✗ | ✓ |
| Add to Folder | ✗ | ✓ |
| Rename | ✗ | ✓ |
| Delete | ✗ | ✗ |
| Share with Others | ✗ | ✗ |
| Change Permissions | ✗ | ✗ |

### Changing Permissions

**Upgrade View to Edit:**
1. Open share settings
2. Find the recipient
3. Change "Can View" to "Can Edit"
4. Confirm change

**Downgrade Edit to View:**
1. Open share settings
2. Find the recipient
3. Change "Can Edit" to "Can View"
4. They immediately lose edit access
5. Any unsaved changes are preserved

[Screenshot: Changing permission levels]

---

## Managing Shared Content

Keep track of everything you've shared and everything shared with you.

### Content You've Shared

**View Your Shares:**
1. Go to Settings → Sharing
2. Click "Shared by Me" tab
3. See all items you've shared

[Screenshot: Shared by me interface]

**Information Displayed:**
- Item name and type
- Who you shared with
- Permission level
- Share date
- Last accessed (if available)

**Quick Actions:**
- Change permissions
- Remove access
- Add more recipients
- View item
- Stop sharing entirely

### Content Shared With You

**Access Shared Items:**
1. Click "Shared" in the sidebar
2. See all items others have shared with you
3. Organized by:
   - Recently shared
   - By owner
   - By type (documents, folders, files)

[Screenshot: Shared with me interface]

**Actions You Can Take:**
- Open and view content
- Edit (if you have permission)
- Add to your favorites
- Copy to your workspace
- Remove from your shared list (doesn't delete original)

### Sharing Notifications

**You'll Be Notified When:**
- Someone shares content with you
- Someone edits shared content (if enabled)
- Someone comments on shared items
- Access permissions change
- Shared content is deleted by owner

**Notification Settings:**
1. Go to Settings → Notifications
2. Customize sharing notifications:
   - Email notifications
   - In-app notifications
   - Push notifications (mobile)

[Screenshot: Notification preferences]

### Sharing Activity Log

**Track Sharing Activity:**
1. Go to Settings → Sharing → Activity Log
2. See timeline of sharing events:
   - New shares created
   - Permissions changed
   - Access removed
   - Content accessed

**Filter Activity:**
- By date range
- By person
- By item
- By action type

[Screenshot: Sharing activity log]

---

## Team Collaboration Features

Advanced features for team collaboration (available in Pro and Enterprise plans).

### Team Workspaces

**What Are Team Workspaces?**
- Shared space for team collaboration
- Centralized content repository
- Shared folder structures
- Common resource libraries

**Setting Up Team Workspace:**
1. Create a main folder (e.g., "Team Workspace")
2. Share with all team members (Can Edit)
3. Create subfolders for different purposes:
   - Projects
   - Templates
   - Resources
   - Archive

[Screenshot: Team workspace folder structure]

### Collaborative Editing

**Real-Time Collaboration:**
- Multiple people can edit simultaneously
- See who else is viewing/editing
- Changes sync in real-time
- No conflicts or overwriting

**Collaboration Indicators:**
- Active users shown at top
- Cursor positions (if supported)
- Recent changes highlighted
- Auto-save every few seconds

[Screenshot: Real-time collaboration interface]

### Comments and Discussions

**Add Comments:**
1. Select text in document
2. Click "Comment" button
3. Type your comment
4. Tag team members with @mentions
5. Post comment

**Comment Features:**
- Thread conversations
- Mark as resolved
- Edit or delete your comments
- Receive notifications on replies
- Filter by resolved/unresolved

[Screenshot: Comment thread on document]

### Mentions and Notifications

**@Mention Team Members:**
- Use `@username` in comments
- They receive instant notification
- Draws attention to specific items
- Requires their immediate input

**Notification Triggers:**
- You're mentioned
- Someone comments on your item
- Shared content is edited
- Permissions change

### Team Templates

**Share Templates:**
- Create template documents
- Share with team
- Everyone uses consistent formats
- Maintain brand standards

**Template Library:**
1. Create "Templates" folder
2. Share with team (Can View)
3. Team members copy templates
4. Customize for their projects

[Screenshot: Team template library]

---

## Enterprise Features

Advanced collaboration for Enterprise plan subscribers.

### Organization Clusters

**What Is a Cluster?**
- Your company's organization
- Centralized user management
- Shared subscription resources
- Admin controls

**Cluster Benefits:**
- Automatic user assignment (by email domain)
- Shared token pool
- Shared storage quota
- Company-wide policies

[Screenshot: Enterprise cluster dashboard]

### User Roles in Enterprise

**Enterprise Admin (Cluster Owner):**
- Manage all cluster users
- Assign roles
- View usage analytics
- Control sharing policies
- Manage subscription

**Enterprise Sub Admin:**
- Assist with user management
- View analytics
- Limited administrative access
- Cannot change subscription

**Enterprise User:**
- Regular team member
- Use shared resources
- Collaborate with team
- Access to all features

### Domain-Based Auto-Assignment

**Automatic Team Assignment:**
1. Your company registers a domain (e.g., @acmecorp.com)
2. Any user registering with that domain automatically joins your cluster
3. They inherit shared subscription
4. Immediate access to team workspaces

**Benefits:**
- No manual user addition needed
- Automatic onboarding
- Consistent access control
- Easy team growth

### Shared Resources

**What's Shared in Enterprise:**

**Token Pool:**
- All team members draw from shared token balance
- No individual token limits
- Team efficiency maximized
- Admin monitors usage

**Storage Quota:**
- Shared storage pool
- No per-user limits
- Centralized file management
- Scalable for team needs

**Subscriptions:**
- One subscription for entire team
- Easier billing management
- Cost-effective scaling
- Predictable expenses

[Screenshot: Enterprise resource dashboard]

### Usage Analytics

**Enterprise Admins Can View:**
- Team member activity
- Token consumption by user
- Storage usage by user
- Most used features
- Generated content statistics
- Cost per user

**Reports Available:**
- Daily/Weekly/Monthly summaries
- User activity reports
- Cost analysis
- Usage trends
- Export to CSV/PDF

[Screenshot: Enterprise analytics dashboard]

### Admin Controls

**Admins Can:**
- Add/remove team members
- Assign/change roles
- Set sharing policies
- Control external sharing
- Enforce 2FA
- Set content retention policies
- Configure SSO (Enterprise+)

**Sharing Policies:**
- Allow/restrict external sharing
- Require encryption for shared files
- Set default permission levels
- Expiration requirements
- Audit all sharing activity

---

## Privacy Settings

Control your privacy and security preferences.

### Profile Privacy

**Control What Others See:**

1. Go to Settings → Privacy
2. Configure:
   - **Profile visibility:** Public, Team Only, Private
   - **Show email:** Yes/No
   - **Show activity:** Yes/No
   - **Allow discovery:** Yes/No

[Screenshot: Privacy settings page]

**Privacy Levels:**

**Public:**
- Anyone can find you
- Profile visible to all users
- Can receive shares from anyone

**Team Only:**
- Only team members can find you
- Profile visible to organization
- Can receive shares from team

**Private:**
- Not discoverable in search
- Profile hidden
- Must be added by email address
- Most restrictive

### Content Privacy

**Default Sharing Settings:**
1. Settings → Privacy → Defaults
2. Set default options for new shares:
   - Default permission level
   - Email notifications on/off
   - Allow resharing by default
   - Default expiration period

**Content Visibility:**
- All your content is private by default
- Only you can access unless explicitly shared
- Deleted content is not recoverable by others
- Shared content visibility controlled by you

### External Sharing Controls

**Restrict External Sharing:**
- Settings → Privacy → External Sharing
- Toggle on/off
- When off, you can only share with registered users
- Prevents accidental public sharing

**Sharing Audit:**
- Review all active shares regularly
- Remove unnecessary access
- Check for expired shares
- Validate permission levels

### Data Security

**Security Features:**
- All data encrypted in transit (HTTPS)
- Files encrypted at rest (AWS S3)
- Secure authentication (JWT tokens)
- Session management
- Auto-logout on inactivity

**Access Logs:**
- Track who accessed your content
- See when and from where
- Detect unusual activity
- Export logs for review

[Screenshot: Access log interface]

### Two-Factor Authentication (2FA)

**Enable 2FA:**
1. Settings → Security → Two-Factor Authentication
2. Choose method:
   - Authenticator app (recommended)
   - SMS codes
   - Email codes
3. Follow setup instructions
4. Save backup codes

**Benefits:**
- Enhanced account security
- Prevent unauthorized access
- Required for sensitive operations
- Peace of mind

[Screenshot: 2FA setup interface]

---

## Best Practices

### 1. Share Intentionally

**Before Sharing, Ask:**
- Who needs access?
- What level of access do they need?
- How long should access last?
- Should they be able to reshare?

**Don't:**
- Share everything with everyone
- Give edit access when view is sufficient
- Leave shares active indefinitely
- Forget to review sharing regularly

### 2. Use Appropriate Permissions

**Can View for:**
- Final deliverables to clients
- Reference materials
- Completed work for review
- Templates (to prevent accidental edits)

**Can Edit for:**
- Active collaboration
- Team workspaces
- Co-authoring documents
- Ongoing projects

### 3. Organize Shared Folders

**Create Clear Structures:**
```
📁 Shared - Client Projects
├── 📁 ABC Corp
│   ├── 📁 Deliverables (Can View)
│   └── 📁 Working Files (Can Edit)
├── 📁 XYZ Inc
│   ├── 📁 Deliverables (Can View)
│   └── 📁 Working Files (Can Edit)
```

**Benefits:**
- Clear separation of access levels
- Easy to manage permissions
- Intuitive for recipients
- Scalable structure

### 4. Communicate Clearly

**When Sharing, Include:**
- Why you're sharing
- What you need from them
- Any deadlines
- Specific areas to focus on

**Example Message:**
```
"Hi Sarah,

I'm sharing the Q1 marketing plan draft for your review.
Please focus on the budget section (page 3) and provide
feedback by Friday, Jan 20.

Thanks!
```

### 5. Set Expiration Dates

**Use Expirations for:**
- Temporary contractor access
- Project-based sharing
- Time-sensitive reviews
- External collaborators

**Benefits:**
- Automatic cleanup
- Reduced security risk
- No forgotten access
- Compliance with policies

### 6. Regular Audits

**Monthly Review:**
- Check all active shares
- Remove unnecessary access
- Update permissions as needed
- Clean up old shares

**Quarterly Review:**
- Review sharing policies
- Update team access
- Verify compliance
- Archive old projects

### 7. Use Comments Effectively

**Comment Guidelines:**
- Be specific and constructive
- Tag relevant people with @mentions
- Mark resolved when addressed
- Keep discussions on-topic

**Example:**
```
@sarah The pricing in this section seems high. Can we
revise based on our competitive analysis? See page 7 for
reference.
```

### 8. Protect Sensitive Information

**Never Share Publicly:**
- Passwords or credentials
- Personal information
- Confidential business data
- Unpublished work

**For Sensitive Content:**
- Use view-only permissions
- Set short expiration dates
- Enable access logging
- Consider watermarking

### 9. Leverage Team Workspaces

**For Teams:**
- Create centralized workspace
- Establish folder conventions
- Use consistent naming
- Document your system

**Example Workspace:**
```
📁 Team Workspace
├── 📁 Active Projects
├── 📁 Templates
├── 📁 Resources
├── 📁 Meeting Notes
└── 📁 Archive
```

### 10. Train Your Team

**Onboard New Members:**
- Share organization guidelines
- Explain folder structure
- Review sharing best practices
- Provide collaboration tips

**Create a Team Guide:**
```
Team Collaboration Guide

Folder Structure: [explain system]
Naming Conventions: [provide examples]
Sharing Guidelines: [list rules]
Communication: [preferred methods]
```

---

## Troubleshooting

### Common Issues

**Issue: Recipient can't see shared content**
- ✓ Verify they're logged into correct account
- ✓ Check spam folder for share notification
- ✓ Confirm share was successful
- ✓ Verify they have MultinotesAI account

**Issue: Can't edit shared document**
- ✓ Check your permission level (might be view-only)
- ✓ Contact owner to upgrade permissions
- ✓ Try copying to your workspace to edit

**Issue: Shared folder missing items**
- ✓ Items may have been moved by owner
- ✓ Refresh the page
- ✓ Check if individual items were unshared
- ✓ Contact owner to verify

**Issue: Share notifications not received**
- ✓ Check notification settings
- ✓ Verify email address is correct
- ✓ Check spam/junk folder
- ✓ Enable in-app notifications

### Getting Help

**Support Resources:**
- **Live Chat:** Instant help with sharing issues
- **Email Support:** support@multinotesai.com
- **Documentation:** Full collaboration guides
- **Video Tutorials:** Step-by-step instructions

---

## Quick Reference

### Sharing Quick Steps

**Share a Document:**
1. Open document
2. Click "Share"
3. Add recipient
4. Set permission
5. Send

**Share a Folder:**
1. Right-click folder
2. Select "Share"
3. Add recipient
4. Set permission
5. Send

**Change Permissions:**
1. Open share settings
2. Find recipient
3. Change level
4. Confirm

**Remove Access:**
1. Open share settings
2. Find recipient
3. Click "Remove"
4. Confirm

### Keyboard Shortcuts

| Action | Windows/Linux | Mac |
|--------|--------------|-----|
| Share | `Ctrl + Shift + S` | `Cmd + Shift + S` |
| View Shares | `Ctrl + Shift + H` | `Cmd + Shift + H` |

---

**Collaborate effectively and securely with MultinotesAI!**

**Need Help?**
- Live Chat: Available in the app
- Email: support@multinotesai.com
- Documentation: https://docs.multinotesai.com

**Last Updated:** November 2025
