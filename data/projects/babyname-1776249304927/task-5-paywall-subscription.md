# 🛠️ Implementation: Paywall + Subscription

**Purpose**: Gate name generation behind a server-enforced usage limit and convert free users to subscribers via StoreKit 2. This is the monetization layer — it turns validated engagement (users who generated names and saved favorites) into revenue.

**Effort**: 1 day

**Dependencies**: Task 2 (AI Name Generation Engine) — the `UsageMeter` and `/api/generate` endpoint exist. Task 3 (Name Card UI + Results Screen) — the results page exists as the surface where the paywall triggers.

**Parallel With**: —

**Blocks**: App Store submission — the app needs a working subscription before review.

**Related**:
- [Solution Architecture](./architecture.md) — Paywall component design, Server-Side Paywall Enforcement pattern
- [Epic](./epic.md) — Task 5 definition, freemium conversion strategy

---

## Overview

### What's Included
- Hard paywall enforcement in the `/api/generate` endpoint — requests beyond the free tier return a `paywall: true` response instead of name cards
- `subscriptions` table in Neon Postgres to store validated Apple receipts per device
- `/api/validate-receipt` backend endpoint for Apple receipt validation
- `StoreKitService` on the frontend — wraps Capacitor's StoreKit 2 plugin for purchase, restore, and status checks
- `PaywallPage` — full-screen subscription offer shown when the free tier is exhausted
- Subscription status check integrated into the generation flow
- Restore purchases functionality for users who reinstall

### What's NOT Included
- Stripe or web-based payments — App Store is the only distribution channel for MVP
- Free trial periods — the 3 free generations *are* the trial; a time-based trial adds complexity without improving conversion signal
- Multiple subscription tiers — one price, one plan; tiering is a post-validation optimization
- Promo codes or referral discounts — no distribution channel for them at MVP scale
- Android billing — iOS-only per the [Architecture](./architecture.md) stack decision

---

## Prerequisites

Before starting:
- Task 2 complete — `UsageMeter` exists in `backend/usage.py`, `/api/generate` endpoint works, `DeviceService` provides device IDs
- Task 3 complete — results page exists and passes `generationsRemaining` to the UI
- **Apple Developer account** enrolled in Apple Small Business Program (15% commission)
- **App Store Connect**: Create the app record and configure a subscription product:
  - Product ID: `com.babyname.pro.monthly` (auto-renewable subscription)
  - Price: $4.99/month (mid-range of the $3.99–$4.99 range from the [Epic](./epic.md); round up for perceived quality)
  - Subscription Group: "Baby Name Pro"
- **Capacitor plugin**: `npm install capacitor-purchases` (RevenueCat's Capacitor plugin) or use `@capawesome/capacitor-purchases` for direct StoreKit 2 access
- Neon Postgres connection string available (same instance as `babyname_usage` table)

**Important choice**: This guide uses the **App Store Server API v2** for server-side receipt validation rather than the deprecated `/verifyReceipt` endpoint. Apple's modern approach uses signed JWS transactions. For MVP simplicity, we validate the transaction on the client side via StoreKit 2 (which handles verification locally) and send the transaction ID to the backend for record-keeping and enforcement. Full server-side JWS validation is a post-validation hardening step.

---

## Implementation Steps

### Step 1: Create the `subscriptions` Table

**File**: `backend/schema.sql` (or run directly against Neon)

**Purpose**: Store active subscription records per device. The backend checks this table before enforcing the free tier limit — if a device has an active subscription, generation is unlimited.

**Pattern**:
```sql
CREATE TABLE IF NOT EXISTS babyname_subscriptions (
    device_id TEXT PRIMARY KEY,
    original_transaction_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

Design notes:
- `device_id` is the primary key, not `original_transaction_id`. One device = one subscription record. If a user resubscribes, the row is updated, not duplicated.
- `original_transaction_id` is Apple's stable identifier for the subscription lifecycle. It persists across renewals and is the key for any future App Store Server API lookups.
- `expires_at` is the subscription expiration. The backend compares this against `NOW()` to determine if the subscription is active. StoreKit 2 handles renewal automatically — the client sends updated expiration dates on each app launch.
- No `status` enum column. A subscription is active if `expires_at > NOW()`. Simplest possible check.

### Step 2: Add Subscription Queries to the Backend

**File**: `backend/subscriptions.py`

**Purpose**: Read and write subscription records. Keeps subscription logic separate from usage tracking (`usage.py`) for clarity, even though both are consulted during generation.

**Pattern**:
```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL")


def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_subscriptions_db():
    """Create the subscriptions table if it doesn't exist."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS babyname_subscriptions (
                    device_id TEXT PRIMARY KEY,
                    original_transaction_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            conn.commit()


def is_subscribed(device_id: str) -> bool:
    """Check if a device has an active subscription."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT expires_at FROM babyname_subscriptions 
                   WHERE device_id = %s AND expires_at > NOW()""",
                (device_id,)
            )
            return cur.fetchone() is not None


def save_subscription(
    device_id: str,
    original_transaction_id: str,
    product_id: str,
    expires_at: datetime
) -> None:
    """Save or update a subscription record for a device."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO babyname_subscriptions 
                    (device_id, original_transaction_id, product_id, expires_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (device_id) DO UPDATE SET
                    original_transaction_id = EXCLUDED.original_transaction_id,
                    product_id = EXCLUDED.product_id,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
            """, (device_id, original_transaction_id, product_id, expires_at))
            conn.commit()


def get_subscription(device_id: str) -> dict | None:
    """Get subscription details for a device."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM babyname_subscriptions WHERE device_id = %s",
                (device_id,)
            )
            return cur.fetchone()
```

Design notes:
- `is_subscribed()` is the hot path — called on every generate request. It's a single indexed lookup by primary key. No performance concern at any scale.
- `save_subscription()` uses UPSERT. Re-validating or renewing updates the existing row. No duplicate handling needed.
- `expires_at > NOW()` is the only subscription check. No grace periods, no "billing retry" states. Apple handles retry logic; the client sends the latest expiration on each app launch.

### Step 3: Enforce the Paywall in the Generate Endpoint

**File**: `backend/app.py`

**Purpose**: Replace the "soft check" from Task 2 with hard paywall enforcement. The generate endpoint now checks subscription status before usage limits. If the user is subscribed, generation is unlimited. If not and the free tier is exhausted, return a paywall response.

Modify the existing `/api/generate` route:

**Pattern**:
```python
from subscriptions import init_subscriptions_db, is_subscribed

# Add to app startup (alongside existing init_db())
with app.app_context():
    if os.getenv("DATABASE_URL"):
        init_db()
        init_subscriptions_db()


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()

    if not data or "preferences" not in data:
        return jsonify({"error": "Missing preferences"}), 400

    preferences = data["preferences"]
    device_id = data.get("deviceId", request.headers.get("X-Device-Id", "anonymous"))

    # --- Paywall gate ---
    if os.getenv("DATABASE_URL"):
        subscribed = is_subscribed(device_id)
        
        if not subscribed:
            usage = get_usage(device_id)
            if usage["limit_reached"]:
                return jsonify({
                    "paywall": True,
                    "generationsUsed": usage["count"],
                    "generationLimit": FREE_GENERATION_LIMIT,
                    "message": "You've used all your free generations. Subscribe to keep discovering names.",
                }), 402  # Payment Required
    else:
        subscribed = False

    # --- Generate names ---
    try:
        names = generate_names(preferences)
    except ValueError as e:
        return jsonify({"error": str(e)}), 502

    # Track usage (only for free tier users)
    remaining = None
    if os.getenv("DATABASE_URL") and not subscribed:
        remaining = increment_usage(device_id)

    return jsonify({
        "names": names,
        "generationsRemaining": remaining,  # null for subscribers (unlimited)
    })
```

Design notes:
- HTTP 402 (Payment Required) is the semantically correct status code. The client checks for 402 to trigger the paywall UI.
- Subscribers skip both the usage check *and* usage incrementing. Their generation count stays frozen at whatever it was when they subscribed — useful for analytics ("how many free generations before conversion?").
- `generationsRemaining: null` for subscribers signals "unlimited" to the client. The results page can hide the counter or show an "unlimited" badge.
- The `paywall` flag in the response body gives the client a reliable boolean to check, independent of HTTP status parsing.
- Import `FREE_GENERATION_LIMIT` from `usage.py` so the paywall response includes the limit for display.

### Step 4: Add the Receipt Validation Endpoint

**File**: `backend/app.py`

**Purpose**: Receive transaction data from the client after a successful StoreKit 2 purchase, validate it, and store the subscription record. The client sends the original transaction ID, product ID, and expiration date — all provided by StoreKit 2's local transaction verification.

**Pattern**:
```python
from subscriptions import save_subscription
from datetime import datetime, timezone


@app.route("/api/validate-receipt", methods=["POST"])
def validate_receipt():
    data = request.get_json()

    device_id = data.get("deviceId")
    original_transaction_id = data.get("originalTransactionId")
    product_id = data.get("productId")
    expires_at_ms = data.get("expiresAt")  # Unix timestamp in milliseconds

    if not all([device_id, original_transaction_id, product_id, expires_at_ms]):
        return jsonify({"error": "Missing required fields"}), 400

    expires_at = datetime.fromtimestamp(
        expires_at_ms / 1000, tz=timezone.utc
    )

    save_subscription(
        device_id=device_id,
        original_transaction_id=original_transaction_id,
        product_id=product_id,
        expires_at=expires_at,
    )

    return jsonify({
        "status": "active",
        "expiresAt": expires_at.isoformat(),
    })
```

Design notes:
- This is a "trust the client" approach. StoreKit 2 verifies the transaction locally using Apple's device-level cryptographic verification. The backend stores the result for enforcement.
- For MVP at 200-user scale, client-side verification is sufficient. A motivated attacker could forge a request to this endpoint — but at validation scale, the risk is a handful of free generations, not material revenue loss.
- **Post-validation hardening**: Replace this with server-side JWS verification using Apple's App Store Server API v2. The `original_transaction_id` stored here is the key needed for that upgrade.
- `expires_at` comes in milliseconds (JavaScript convention) and is converted to UTC datetime for Postgres.

### Step 5: Add a Subscription Status Check Endpoint

**File**: `backend/app.py`

**Purpose**: Let the client check subscription status on app launch. The client calls this to determine whether to show the paywall or allow unlimited generation. Useful for restore-purchases flow and for refreshing expired subscriptions.

**Pattern**:
```python
from subscriptions import get_subscription


@app.route("/api/subscription-status", methods=["GET"])
def subscription_status():
    device_id = request.args.get("deviceId")
    if not device_id:
        return jsonify({"error": "Missing deviceId"}), 400

    sub = get_subscription(device_id)

    if sub and sub["expires_at"] > datetime.now(timezone.utc):
        return jsonify({
            "subscribed": True,
            "productId": sub["product_id"],
            "expiresAt": sub["expires_at"].isoformat(),
        })

    # Not subscribed or expired — include usage info
    usage = get_usage(device_id)
    return jsonify({
        "subscribed": False,
        "generationsUsed": usage["count"],
        "generationsRemaining": usage["remaining"],
        "generationLimit": FREE_GENERATION_LIMIT,
    })
```

Design notes:
- GET request because it's a read with no side effects. `deviceId` as a query param.
- Returns different shapes for subscribed vs. free users. The client needs different data for each state.
- Called once on app launch, not on every generation. The generate endpoint handles per-request enforcement independently.

### Step 6: Create the StoreKit Service

**File**: `src/app/services/storekit.service.ts`

**Purpose**: Wrap StoreKit 2 operations — load products, purchase a subscription, restore purchases, and check entitlements. This is the payment plumbing on the client side. Uses Capacitor's `@capawesome/capacitor-in-app-purchases` plugin for direct StoreKit 2 access.

```bash
npm install @capawesome/capacitor-in-app-purchases
npx cap sync
```

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Capacitor } from '@capacitor/core';
import {
  InAppPurchases,
  Product,
  Transaction,
  ProductType,
} from '@capawesome/capacitor-in-app-purchases';
import { DeviceService } from './device.service';
import { environment } from '../../environments/environment';
import { firstValueFrom } from 'rxjs';

const PRODUCT_ID = 'com.babyname.pro.monthly';

export interface SubscriptionStatus {
  subscribed: boolean;
  productId?: string;
  expiresAt?: string;
  generationsUsed?: number;
  generationsRemaining?: number;
  generationLimit?: number;
}

@Injectable({ providedIn: 'root' })
export class StoreKitService {

  private product: Product | null = null;

  constructor(
    private http: HttpClient,
    private deviceService: DeviceService,
  ) {}

  async initialize(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    // Load the subscription product
    const { products } = await InAppPurchases.getProducts({
      productIds: [PRODUCT_ID],
      productType: ProductType.SUBSCRIPTION,
    });

    this.product = products.length > 0 ? products[0] : null;

    // Listen for completed transactions (purchases + renewals)
    InAppPurchases.addListener('transactionUpdate', async (transaction) => {
      if (transaction.transactionState === 'purchased') {
        await this.handleCompletedTransaction(transaction);
        await InAppPurchases.finishTransaction({
          transactionId: transaction.transactionId,
        });
      }
    });
  }

  getProduct(): Product | null {
    return this.product;
  }

  getFormattedPrice(): string {
    return this.product?.priceFormatted ?? '$4.99/month';
  }

  async purchase(): Promise<boolean> {
    if (!this.product) return false;

    try {
      await InAppPurchases.purchaseProduct({
        productId: PRODUCT_ID,
        productType: ProductType.SUBSCRIPTION,
      });
      return true;
    } catch (err: any) {
      if (err?.code === 'USER_CANCELLED') return false;
      throw err;
    }
  }

  async restorePurchases(): Promise<boolean> {
    const { transactions } = await InAppPurchases.restorePurchases();

    for (const transaction of transactions) {
      if (transaction.productId === PRODUCT_ID) {
        await this.handleCompletedTransaction(transaction);
        return true;
      }
    }

    return false;
  }

  async checkStatus(): Promise<SubscriptionStatus> {
    const deviceId = await this.deviceService.getDeviceId();
    return firstValueFrom(
      this.http.get<SubscriptionStatus>(
        `${environment.apiUrl}/api/subscription-status`,
        { params: { deviceId } }
      )
    );
  }

  private async handleCompletedTransaction(transaction: Transaction): Promise<void> {
    const deviceId = await this.deviceService.getDeviceId();

    await firstValueFrom(
      this.http.post(`${environment.apiUrl}/api/validate-receipt`, {
        deviceId,
        originalTransactionId: transaction.originalTransactionId,
        productId: transaction.productId,
        expiresAt: transaction.expirationDate,
      })
    );
  }
}
```

Design notes:
- `initialize()` is called once at app startup (in `AppComponent.ngOnInit`). It loads the product and sets up the transaction listener.
- The `transactionUpdate` listener handles both initial purchases and automatic renewals. When Apple renews a subscription, StoreKit 2 fires this event, and the backend record is updated with the new expiration.
- `finishTransaction()` is required by StoreKit 2. Without it, Apple retries the transaction notification indefinitely.
- `USER_CANCELLED` is not an error — it means the user dismissed the purchase sheet. Return `false` to let the UI handle it gracefully.
- `getFormattedPrice()` returns the localized price from Apple (e.g., "$4.99" in the US, "€4.49" in the EU). Falls back to a hardcoded string for non-native platforms.
- The browser path (`!Capacitor.isNativePlatform()`) silently no-ops. During development, test paywall UI separately from actual StoreKit flows.

### Step 7: Create the Paywall Page

**File**: `src/app/pages/paywall/paywall.page.ts`

**Purpose**: Full-screen subscription offer shown when the free tier is exhausted. This is a modal-style page that overlays the results flow. It must clearly communicate the value proposition and make purchasing frictionless.

```bash
ionic generate page pages/paywall
```

**Pattern**:
```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, ModalController, ToastController } from '@ionic/angular';
import { StoreKitService, SubscriptionStatus } from '../../services/storekit.service';

@Component({
  selector: 'app-paywall',
  standalone: true,
  imports: [CommonModule, IonicModule],
  template: `
    <ion-content class="paywall-content" [fullscreen]="true">
      <div class="paywall-container">

        <!-- Close button -->
        <ion-button fill="clear" class="close-btn" (click)="dismiss(false)">
          <ion-icon name="close" slot="icon-only"></ion-icon>
        </ion-button>

        <!-- Hero -->
        <div class="hero">
          <div class="icon-circle">
            <ion-icon name="sparkles"></ion-icon>
          </div>
          <h1>Unlock Unlimited Names</h1>
          <p class="subtitle">
            You've used your {{ generationsUsed }} free generations.
            Subscribe to keep discovering the perfect name.
          </p>
        </div>

        <!-- Value props -->
        <div class="features">
          <div class="feature-row">
            <ion-icon name="infinite-outline" color="primary"></ion-icon>
            <span>Unlimited name generations</span>
          </div>
          <div class="feature-row">
            <ion-icon name="refresh-outline" color="primary"></ion-icon>
            <span>Regenerate with new preferences anytime</span>
          </div>
          <div class="feature-row">
            <ion-icon name="heart-outline" color="primary"></ion-icon>
            <span>Save and share unlimited favorites</span>
          </div>
          <div class="feature-row">
            <ion-icon name="flash-outline" color="primary"></ion-icon>
            <span>AI-powered, personalized to your taste</span>
          </div>
        </div>

        <!-- Price + CTA -->
        <div class="cta-section">
          <ion-button
            expand="block"
            size="large"
            (click)="subscribe()"
            [disabled]="isPurchasing"
          >
            <ion-spinner *ngIf="isPurchasing" name="crescent" slot="start"></ion-spinner>
            {{ isPurchasing ? 'Processing...' : 'Subscribe for ' + price }}
          </ion-button>
          <p class="price-note">Auto-renews monthly. Cancel anytime.</p>
        </div>

        <!-- Restore -->
        <div class="restore-section">
          <ion-button
            fill="clear"
            size="small"
            (click)="restore()"
            [disabled]="isRestoring"
          >
            {{ isRestoring ? 'Restoring...' : 'Restore Purchases' }}
          </ion-button>
        </div>

      </div>
    </ion-content>
  `,
  styles: [`
    .paywall-content {
      --background: linear-gradient(180deg, #f0f4ff 0%, #ffffff 40%);
    }
    .paywall-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px;
      min-height: 100%;
      position: relative;
    }
    .close-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      --color: var(--ion-color-medium);
    }
    .hero {
      text-align: center;
      margin-top: 48px;
      margin-bottom: 32px;
    }
    .icon-circle {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: var(--ion-color-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px;
    }
    .icon-circle ion-icon {
      font-size: 36px;
      color: white;
    }
    h1 {
      font-size: 1.8rem;
      font-weight: 700;
      margin: 0;
    }
    .subtitle {
      color: var(--ion-color-medium-shade);
      margin-top: 8px;
      font-size: 1rem;
      line-height: 1.5;
      max-width: 300px;
    }
    .features {
      width: 100%;
      max-width: 320px;
      margin-bottom: 32px;
    }
    .feature-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 0;
      font-size: 1rem;
    }
    .feature-row ion-icon {
      font-size: 1.4rem;
      flex-shrink: 0;
    }
    .cta-section {
      width: 100%;
      max-width: 320px;
    }
    .price-note {
      text-align: center;
      color: var(--ion-color-medium);
      font-size: 0.85rem;
      margin-top: 8px;
    }
    .restore-section {
      margin-top: 16px;
    }
  `]
})
export class PaywallPage implements OnInit {
  price = '';
  generationsUsed = 3;
  isPurchasing = false;
  isRestoring = false;

  constructor(
    private modalCtrl: ModalController,
    private toastCtrl: ToastController,
    private storeKitService: StoreKitService,
  ) {}

  ngOnInit(): void {
    this.price = this.storeKitService.getFormattedPrice();
  }

  async subscribe(): Promise<void> {
    this.isPurchasing = true;
    try {
      const purchased = await this.storeKitService.purchase();
      if (purchased) {
        await this.dismiss(true);
      }
    } catch (err) {
      const toast = await this.toastCtrl.create({
        message: 'Purchase failed. Please try again.',
        duration: 3000,
        position: 'bottom',
        color: 'danger',
      });
      await toast.present();
    } finally {
      this.isPurchasing = false;
    }
  }

  async restore(): Promise<void> {
    this.isRestoring = true;
    try {
      const restored = await this.storeKitService.restorePurchases();
      if (restored) {
        await this.dismiss(true);
      } else {
        const toast = await this.toastCtrl.create({
          message: 'No active subscription found.',
          duration: 3000,
          position: 'bottom',
        });
        await toast.present();
      }
    } finally {
      this.isRestoring = false;
    }
  }

  async dismiss(purchased: boolean): Promise<void> {
    await this.modalCtrl.dismiss({ purchased });
  }
}
```

Design notes:
- Presented as a **modal**, not a route. The user's place in the results flow is preserved — dismissing the paywall returns them to exactly where they were. No navigation state to manage.
- The close button is always visible. Apple rejects apps that trap users on paywall screens with no escape.
- "Auto-renews monthly. Cancel anytime." is required by App Store Review Guidelines (section 3.1.2). Missing this causes rejection.
- `generationsUsed` is passed in when the modal is created (from the 402 response). Shows the user how much value they already got.
- The feature list is short and benefit-focused. No technical jargon. Parents care about "unlimited" and "personalized," not implementation details.
- Restore purchases is required by Apple. Users who reinstall or switch devices need a way to recover their subscription without repurchasing.

### Step 8: Wire the Paywall into the Generation Flow

**File**: `src/app/pages/preferences/preferences.page.ts` (extend the `submit` method)

**Purpose**: Intercept the 402 paywall response from the generate endpoint and present the paywall modal. If the user subscribes, retry the generation automatically.

**Pattern**:
```typescript
import { ModalController } from '@ionic/angular';
import { PaywallPage } from '../paywall/paywall.page';
import { HttpErrorResponse } from '@angular/common/http';

// Add to constructor:
constructor(
  // ...existing deps
  private modalCtrl: ModalController,
) {}

async submit(): Promise<void> {
  await this.prefCache.save(this.preferences);
  this.isGenerating = true;

  const deviceId = await this.deviceService.getDeviceId();

  this.generationService.generate(this.preferences, deviceId).subscribe({
    next: (response) => {
      this.isGenerating = false;
      this.router.navigate(['/results'], {
        state: {
          names: response.names,
          generationsRemaining: response.generationsRemaining,
          preferences: this.preferences,
        }
      });
    },
    error: async (err: HttpErrorResponse) => {
      this.isGenerating = false;

      if (err.status === 402) {
        // Paywall triggered — show subscription modal
        const purchased = await this.presentPaywall(err.error);
        if (purchased) {
          // Retry generation after successful purchase
          this.submit();
        }
      } else {
        console.error('Generation failed:', err);
      }
    }
  });
}

private async presentPaywall(paywallData: any): Promise<boolean> {
  const modal = await this.modalCtrl.create({
    component: PaywallPage,
    componentProps: {
      generationsUsed: paywallData.generationsUsed ?? 3,
    },
  });

  await modal.present();
  const { data } = await modal.onDidDismiss();
  return data?.purchased === true;
}
```

Design notes:
- The paywall appears *in response to* the 402, not preemptively. The user taps "Find Names," the backend says "pay first," and the paywall slides up. This feels natural — the intent (generate names) is clear, so the paywall is a gate on an action they want to take. Higher conversion than a preemptive "you're out of free tries" screen.
- If the user subscribes, `submit()` is called again. The backend now sees an active subscription and allows the generation. No special "subscriber retry" path needed.
- If the user dismisses the paywall without subscribing, nothing happens. They stay on the preferences page. No nagging, no countdown — they can come back later.

### Step 9: Initialize StoreKit on App Startup

**File**: `src/app/app.component.ts`

**Purpose**: Call `StoreKitService.initialize()` when the app launches. This loads the product and sets up the transaction listener for renewals.

**Pattern**:
```typescript
import { StoreKitService } from './services/storekit.service';

// In constructor or ngOnInit:
constructor(private storeKitService: StoreKitService) {
  this.storeKitService.initialize();
}
```

### Step 10: Show Remaining Generations on the Results Page

**File**: `src/app/pages/results/results.page.ts` (extend)

**Purpose**: Display a subtle indicator of remaining free generations on the results page. This creates awareness without being pushy — the user sees "2 generations left" and naturally understands there's a limit. When they hit the wall, the paywall isn't a surprise.

**Pattern**:
```html
<!-- Add to results page template, below the header -->
<div class="generations-remaining" *ngIf="generationsRemaining !== null && generationsRemaining !== undefined">
  <ion-chip [color]="generationsRemaining <= 1 ? 'warning' : 'medium'" outline>
    <ion-icon name="flash-outline"></ion-icon>
    <ion-label>
      {{ generationsRemaining === 0 
         ? 'No free generations left' 
         : generationsRemaining + ' free generation' + (generationsRemaining !== 1 ? 's' : '') + ' remaining' 
      }}
    </ion-label>
  </ion-chip>
</div>
```

```css
.generations-remaining {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}
```

Design notes:
- `null` means the user is subscribed — hide the counter entirely. Subscribers shouldn't see usage tracking UI.
- Warning color at 1 or 0 remaining creates urgency without being aggressive.
- This is informational, not a gate. The actual gate is the 402 response from the backend. This chip just prevents surprise.

### Step 11: Update the GenerationResponse Type

**File**: `src/app/models/name-card.model.ts`

**Purpose**: The 402 paywall response has a different shape than the success response. Add a type for it so the error handler in Step 8 has type safety.

**Pattern**:
```typescript
// Add alongside existing interfaces

export interface PaywallResponse {
  paywall: true;
  generationsUsed: number;
  generationLimit: number;
  message: string;
}
```

### Step 12: Add the Paywall Route (Fallback)

**File**: `src/app/app-routing.module.ts` (or `app.routes.ts`)

**Purpose**: While the paywall is normally presented as a modal, register it as a route too. This allows deep-linking and handles edge cases where the modal approach isn't appropriate (e.g., app launch directly to paywall after expiration).

**Pattern**:
```typescript
{
  path: 'paywall',
  loadComponent: () =>
    import('./pages/paywall/paywall.page').then(m => m.PaywallPage),
},
```

---

## Verification

### Backend paywall enforcement:

```bash
cd backend && python app.py
```

```bash
# Use up all 3 free generations (run 3 times with same device ID)
for i in 1 2 3; do
  curl -s -X POST http://localhost:3200/api/generate \
    -H "Content-Type: application/json" \
    -d '{"preferences": {"gender": "girl"}, "deviceId": "test-paywall-1"}' \
    | python -m json.tool | head -5
  echo "---"
done

# 4th request — should return 402 with paywall response
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3200/api/generate \
  -H "Content-Type: application/json" \
  -d '{"preferences": {"gender": "girl"}, "deviceId": "test-paywall-1"}'
# Expected: 402

# Check the paywall response body
curl -s -X POST http://localhost:3200/api/generate \
  -H "Content-Type: application/json" \
  -d '{"preferences": {"gender": "girl"}, "deviceId": "test-paywall-1"}' \
  | python -m json.tool
# Expected: {"paywall": true, "generationsUsed": 3, "generationLimit": 3, "message": "..."}
```

### Receipt validation:

```bash
# Simulate a subscription purchase
curl -s -X POST http://localhost:3200/api/validate-receipt \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "test-paywall-1",
    "originalTransactionId": "test-txn-001",
    "productId": "com.babyname.pro.monthly",
    "expiresAt": 1767225600000
  }' | python -m json.tool
# Expected: {"status": "active", "expiresAt": "2025-12-31T00:00:00+00:00"}

# Now generate should work again (subscriber bypasses paywall)
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3200/api/generate \
  -H "Content-Type: application/json" \
  -d '{"preferences": {"gender": "girl"}, "deviceId": "test-paywall-1"}'
# Expected: 200
```

### Subscription status:

```bash
# Check subscribed device
curl -s "http://localhost:3200/api/subscription-status?deviceId=test-paywall-1" \
  | python -m json.tool
# Expected: {"subscribed": true, "productId": "com.babyname.pro.monthly", ...}

# Check unsubscribed device
curl -s "http://localhost:3200/api/subscription-status?deviceId=never-subscribed" \
  | python -m json.tool
# Expected: {"subscribed": false, "generationsUsed": 0, "generationsRemaining": 3, ...}
```

### StoreKit testing (iOS Simulator):

1. Configure a StoreKit Configuration file in Xcode (`BabyName.storekit`)
2. Add the `com.babyname.pro.monthly` product with $4.99 price
3. Build to Simulator: `npx cap run ios`
4. Use up 3 free generations
5. Tap "Find Names" again — paywall modal should appear
6. Tap "Subscribe" — StoreKit sandbox purchase sheet appears
7. Complete the sandbox purchase
8. Paywall dismisses, generation retries automatically
9. Subsequent generations should work without paywall

**Expected Result**: The paywall appears only after the free tier is exhausted. Subscribing immediately unlocks generation. The remaining-generations counter disappears for subscribers.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 5 as done
2. Configure the subscription in App Store Connect (product ID, pricing, subscription group, review screenshot)
3. Test the full purchase flow in TestFlight sandbox before submitting for review
4. Ensure the paywall page includes all required disclosures for App Store review (auto-renewal terms, price, cancel instructions)
5. Submit the app for App Store review

---

## Related Documents

- [Solution Architecture](./architecture.md) — Paywall component design, Server-Side Paywall Enforcement pattern, Technology Stack decisions
- [Epic](./epic.md) — Task 5 scope, freemium strategy, success criteria for paywall activation
- [Analysis](./analysis.md) — Market pricing context, competitor monetization patterns
- [Task 2: AI Name Generation Engine](./task-2-ai-name-generation-engine.md) — `UsageMeter`, `/api/generate` endpoint, `DeviceService` built there, extended here
- [Task 3: Name Card UI + Results Screen](./task-3-name-card-ui-results-screen.md) — Results page where remaining-generations counter is added
- [Timeline](./timeline.md) — Status tracking