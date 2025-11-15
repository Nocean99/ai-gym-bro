# 🧪 TestFlight Beta Testing Guide

Complete guide to testing Gym Bro with friends and family before public release.

---

## What is TestFlight?

TestFlight is Apple's official beta testing platform. It lets you:
- ✅ Test your app before public release
- ✅ Invite up to 10,000 external testers (friends, family, anyone)
- ✅ Get feedback and crash reports
- ✅ Distribute updates easily
- ✅ No App Store review for internal testing (up to 100 people)

---

## 📋 Prerequisites (Same as App Store)

You still need:

### 1. Apple Developer Account
- Enroll: https://developer.apple.com/programs/
- Cost: $99/year
- Approval: 1-2 days
- **Required even for TestFlight**

### 2. App Icons (Can't Use Flutter Defaults!)
**This is still required for TestFlight**

Options:
- **Quick & Easy**: Use AI tools (DALL-E, Midjourney) + [appicon.co](https://appicon.co)
- **Professional**: Hire on Fiverr ($20-50)
- **DIY**: Design in Figma/Canva, export at 1024x1024

**Location**: `mobile/ios/Runner/Assets.xcassets/AppIcon.appiconset/`

### 3. macOS with Xcode
- Need a Mac to build iOS apps
- Xcode is free from Mac App Store

---

## 🚀 TestFlight Setup Steps

### Step 1: Create App in App Store Connect

1. Go to https://appstoreconnect.apple.com
2. Click **"My Apps"** → **"+"** → **"New App"**
3. Fill in:
   - **Platform**: iOS
   - **Name**: Gym Bro
   - **Primary Language**: English
   - **Bundle ID**: Select `com.gymbro.app` (or create it if not exists)
   - **SKU**: `gymbro-001` (any unique identifier)
   - **User Access**: Full Access

4. Click **"Create"**

**Note**: You're creating the app listing but NOT submitting for review yet!

---

### Step 2: Configure App Information (Minimal for TestFlight)

You only need minimal info for TestFlight:

1. **App Information** (left sidebar):
   - Category: Health & Fitness (required)
   - Age Rating: Click "Edit" and complete questionnaire

2. **Pricing and Availability**:
   - Price: Free
   - Availability: All countries (or select specific ones)

**You DON'T need for TestFlight**:
- ❌ Screenshots (only needed for App Store release)
- ❌ App Description (only for public release)
- ❌ Keywords (only for public release)
- ❌ Privacy Policy URL (good to have, but not required for internal testing)

---

### Step 3: Build Your App for TestFlight

#### A. On Your Mac, Open Xcode

```bash
cd /path/to/ai-gym-bro/mobile/ios
open Runner.xcworkspace
```

#### B. Configure Signing & Capabilities

1. Click **"Runner"** in the left panel (top-level)
2. Select **"Runner"** target
3. Go to **"Signing & Capabilities"** tab
4. Configure:
   - **Team**: Select your Apple Developer team
   - **Bundle Identifier**: `com.gymbro.app`
   - **Automatically manage signing**: ✅ (recommended)

Xcode will automatically:
- Create certificates
- Create provisioning profiles
- Handle code signing

#### C. Select Build Destination

- Top toolbar: Select **"Any iOS Device (arm64)"**
- Do NOT select a simulator

#### D. Archive the App

1. Menu: **Product** → **Archive**
2. Wait for build (2-5 minutes)
3. Xcode Organizer opens automatically

#### E. Distribute to App Store Connect

In Xcode Organizer:

1. Select your archive
2. Click **"Distribute App"**
3. Select **"App Store Connect"**
4. Click **"Upload"**
5. Click **"Next"** through the options:
   - ✅ Include bitcode: Yes
   - ✅ Upload symbols: Yes
   - ✅ Manage version: Automatic
6. Click **"Upload**"

**Processing Time**: 10-30 minutes for Apple to process your build

---

### Step 4: Set Up TestFlight Beta Testing

After your build is processed:

#### A. Go to TestFlight Tab

1. In App Store Connect, select your app
2. Click **"TestFlight"** tab at the top
3. Wait for build to show as **"Ready to Submit"** or **"Ready to Test"**

#### B. Choose Testing Type

You have 2 options:

##### **Option 1: Internal Testing** (Fastest, No Review)
- Up to 100 testers
- Testers must be added to your App Store Connect team
- No App Review required
- Start testing immediately

##### **Option 2: External Testing** (Recommended for Friends/Family)
- Up to 10,000 testers
- Invite anyone with email
- **Requires lightweight App Review** (usually 1-2 days)
- Best for friends and family

**For friends and family, use External Testing!**

---

### Step 5: Set Up External Testing Group

1. In TestFlight tab, click **"External Testing"** (left sidebar)
2. Click **"+"** to create a new group
3. Name it: `Friends and Family` (or whatever you want)
4. Select your build
5. Click **"Next"**

#### Fill in Beta App Review Information:

**Beta App Description**:
```
Gym Bro is an AI-powered workout tracking app. Users can log workouts using natural language, get personalized AI recommendations, and track their fitness progress over time.
```

**Feedback Email**: Your email address

**What to Test**:
```
Please test:
- Logging workouts using natural language
- Asking the AI for workout recommendations
- Viewing workout history and progress charts
- Creating an account and logging in
```

**Test Account** (if login required):
- Username: testuser
- Password: (create a test password)

**Notes for Reviewers**:
```
This is a beta test for friends and family. The app uses OpenAI's API to provide AI-powered workout recommendations and tracking.
```

6. Click **"Submit for Review"**

**Review Time**: Usually 1-2 days for TestFlight review (faster than full App Store review)

---

### Step 6: Invite Testers

Once approved for external testing:

#### Method 1: Invite by Email

1. Go to your External Testing group
2. Click **"Testers"** → **"+"**
3. Add email addresses (one per line):
   ```
   friend1@email.com
   friend2@email.com
   family@email.com
   ```
4. Click **"Add"**

They'll receive an email invitation!

#### Method 2: Public Link (Even Easier!)

1. Go to your External Testing group
2. Click **"Enable Public Link"**
3. Copy the link (looks like: `https://testflight.apple.com/join/XXXXXXXX`)
4. Share this link with anyone:
   - Text message
   - Email
   - Social media
   - Group chat

Anyone with the link can join!

---

### Step 7: Testers Install TestFlight

Your testers need to:

1. **Install TestFlight app** (free on App Store)
2. **Accept invitation**:
   - Via email: Click "View in TestFlight"
   - Via public link: Click link → Opens TestFlight
3. **Click "Install"** in TestFlight
4. **Start testing!**

---

## 📱 What Testers Will See

After installing from TestFlight:

- App appears on home screen as **"Gym Bro β"** (with beta badge)
- Can use the app normally
- Can send feedback directly in TestFlight app
- Automatically get updates when you release new builds

---

## 🔄 Releasing Updates to Testers

When you fix bugs or add features:

1. **Build new version** in Xcode (increment build number)
2. **Archive** → **Upload to App Store Connect**
3. **Wait for processing** (10-30 min)
4. **Add build to your TestFlight group**
5. **Testers automatically get update notification**

No need to re-invite testers!

---

## 📊 Getting Feedback

### View Crash Reports

1. App Store Connect → Your App → TestFlight
2. Click on your build
3. View crash reports and metrics

### Testers Can Send Feedback

From TestFlight app:
- Shake iPhone → "Send Beta Feedback"
- Attach screenshots
- Describe issues

You see feedback in App Store Connect.

---

## ⚠️ Important TestFlight Limits

### Build Expiration
- TestFlight builds expire after **90 days**
- You must upload a new build every 90 days
- Testers automatically get notified

### Tester Limits
- **Internal**: 100 testers (App Store Connect users)
- **External**: 10,000 testers (anyone)
- **Devices**: Each tester can use up to 30 devices

### Review Requirements
- **Internal**: No review needed
- **External**: Lightweight review (1-2 days) for first build
- **Updates**: Usually no re-review unless major changes

---

## 🎯 Recommended Testing Workflow

### Week 1: Internal Testing
1. Add yourself and close team members
2. Test core functionality
3. Fix critical bugs
4. Upload new builds as needed

### Week 2-3: External Testing
1. Submit for external beta review
2. Once approved, invite friends and family
3. Share public link in your circles
4. Collect feedback
5. Fix bugs and iterate

### Week 4+: Prepare for Public Release
1. Finalize app based on feedback
2. Create screenshots
3. Write app description
4. Add privacy policy
5. Submit for full App Store review

---

## 🐛 Common Issues & Solutions

### "No valid signing identity found"
**Solution**:
- Make sure you're enrolled in Apple Developer Program
- Xcode → Preferences → Accounts → Download Manual Profiles

### "Bundle identifier is unavailable"
**Solution**:
- Go to developer.apple.com
- Create App ID manually with `com.gymbro.app`
- Try again in Xcode

### Build stuck "Processing" for hours
**Solution**:
- Usually resolves within 30 min
- If >2 hours, contact Apple Developer Support
- Sometimes just needs patience

### Testers can't install
**Common causes**:
- Need iOS 13+ (check your minimum deployment target)
- Need space on device (app + TestFlight)
- Wrong Apple ID (must match invitation email)

---

## 📧 Email Template for Testers

Send this to your friends and family:

```
Subject: Help Me Test My New App - Gym Bro! 💪

Hey!

I built an app called Gym Bro - it's an AI-powered workout tracker that helps you log workouts and get personalized recommendations.

I'd love your help testing it before I launch publicly!

To test:
1. Install TestFlight (free app from App Store)
2. Click this link: [YOUR TESTFLIGHT LINK]
3. Install Gym Bro
4. Try it out and let me know what you think!

What to test:
- Log a workout (try: "did 3 sets of 10 pushups")
- Ask the AI for recommendations
- Check out your workout history

I really appreciate your help! Let me know if you find any bugs or have suggestions.

Thanks!
```

---

## 🎉 After Successful Beta Testing

Once you're happy with feedback and stability:

1. **Prepare for public release**:
   - Create app screenshots
   - Write compelling description
   - Add keywords for SEO
   - Upload privacy policy

2. **Create new version** in App Store Connect
3. **Submit for full App Review**
4. **Wait for approval** (1-7 days typically)
5. **Release to the world!** 🚀

---

## 💡 Pro Tips

### Get Quality Feedback
- Ask specific questions
- Create a feedback form (Google Forms)
- Incentivize testing (free premium features, etc.)

### Track Issues
- Use GitHub Issues for bug reports
- Create a spreadsheet for feature requests
- Prioritize based on frequency

### Communicate with Testers
- Send update notes with each build
- Thank them for their time
- Show how their feedback helped

### Version Numbers
- Use semantic versioning: `1.0.0 (1)`
- Increment build number for each TestFlight upload
- Version number for major releases

---

## 📞 Support Resources

- **TestFlight Help**: https://developer.apple.com/testflight/
- **App Review Guidelines**: https://developer.apple.com/app-store/review/guidelines/
- **Apple Developer Forums**: https://developer.apple.com/forums/
- **Your Documentation**: See DEPLOYMENT_COMPLETE.md for full App Store guide

---

## ✅ Quick Checklist

Before inviting testers:

- [ ] App icons created and added
- [ ] Apple Developer account enrolled ($99/year)
- [ ] App created in App Store Connect
- [ ] Build uploaded and processed
- [ ] External testing group created
- [ ] Beta review submitted
- [ ] Public link enabled (optional)
- [ ] Test account credentials ready
- [ ] Tester invitation email/message prepared

**Ready to test!** 🧪

---

**Questions?** Check DEPLOYMENT_COMPLETE.md for more details or reach out for help!

Good luck with your beta test! 💪
