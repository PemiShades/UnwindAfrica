# Unwind Africa for iOS and Android

This is a standalone Expo / React Native mobile app. Its Home, Getaways, Savings, Vote and Profile areas are native screens; it does not embed the website. It uses Django as the authoritative data and payment service. Package browsing and nominee previews are native. The existing secured booking and vote payment pages open in the device browser to complete Paystack checkout.

## Local development

From this folder:

```powershell
npm install
$env:EXPO_PUBLIC_API_BASE_URL="http://10.0.2.2:8000"
npm start
```

Use `http://localhost:8000` for an iOS simulator, `http://10.0.2.2:8000` for the Android emulator, or the computer’s LAN address for a physical device. Set `EXPO_PUBLIC_API_BASE_URL` to the public HTTPS domain for release builds. Do not put Paystack secret keys in this app.

## Member features and API

- `GET /api/v1/packages/` — live packages and pricing.
- `GET /api/v1/voting/campaigns/` — campaigns, nominee previews and vote totals.
- `POST /api/v1/auth/request-code/` and `/api/v1/auth/verify-code/` — member email-code sign-in.
- `GET /api/v1/dashboard/` — the signed-in member’s getaway savings, Rest Points, frozen points, reward tokens, orders and vote history.

The token is stored with Expo SecureStore. Django remains responsible for validating orders and payments. Rest Points and reward tokens are loyalty balances, not withdrawable cash.

## iOS and Android release builds

The project is configured for Expo SDK 58 and native bundle identifiers `com.unwindafrica.mobile`. Install EAS CLI, configure the Expo project, then create an EAS build for each store target. iOS release builds require an Apple developer account. Set the production API URL and verify the production email, database, HTTPS and Paystack configuration before store submission.
