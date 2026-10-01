"use client";

import { useState } from "react";
import { Card, CardHeader, CardBody } from "@/components/ui";

interface RazorpayCheckoutProps {
  product: string;
  amount?: number;
  description?: string;
  onPaymentSuccess?: (response: any) => void;
  onPaymentFailure?: (error: any) => void;
}

export function RazorpayCheckout({
  product,
  amount,
  description = `Purchase ${product}`,
  onPaymentSuccess,
  onPaymentFailure,
}: RazorpayCheckoutProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");

  // Load Razorpay script dynamically
  const loadRazorpay = async () => {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve(window.Razorpay);
      script.onerror = () => reject(new Error("Failed to load Razorpay script"));
      document.body.appendChild(script);
    });
  };

  const handleCheckout = async () => {
    try {
      setLoading(true);
      setError(null);

      // Validate email
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setError("Please enter a valid email address");
        setLoading(false);
        return;
      }

      // Step 1: Create order on backend
      const orderResponse = await fetch("/api/blackboxops/razorpay-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product,
          customerName: name || undefined,
          customerEmail: email,
          customerContact: phone || undefined,
        }),
      });

      if (!orderResponse.ok) {
        const errorData = await orderResponse.json();
        setError(errorData.error || "Failed to create order");
        setLoading(false);
        return;
      }

      const orderData = await orderResponse.json();

      if (orderData.error) {
        setError(orderData.error);
        setLoading(false);
        return;
      }

      if (orderData.sold_out) {
        setError(`This product is sold out. ${orderData.error}`);
        setLoading(false);
        return;
      }

      // Step 2: Load Razorpay and open checkout
      const Razorpay = (await loadRazorpay()) as any;

      const checkoutOptions = {
        key: orderData.keyId,
        amount: orderData.amount,
        currency: orderData.currency || "INR",
        name: "BlackboxOps",
        description,
        order_id: orderData.order_id,
        prefill: {
          name: name || "",
          email: email,
          contact: phone || "",
        },
        handler: async (response: any) => {
          try {
            // Step 3: Verify signature on backend
            const verifyResponse = await fetch(
              "/api/blackboxops/razorpay-verify",
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  orderId: orderData.order_id,
                  paymentId: response.razorpay_payment_id,
                  signature: response.razorpay_signature,
                }),
              }
            );

            if (!verifyResponse.ok) {
              throw new Error("Signature verification failed");
            }

            const verifyData = await verifyResponse.json();

            if (!verifyData.verified) {
              setError("Payment verification failed. Please contact support.");
              onPaymentFailure?.(verifyData);
              return;
            }

            // Payment successful!
            setLoading(false);
            onPaymentSuccess?.(verifyData);
          } catch (err) {
            const message =
              err instanceof Error ? err.message : "Payment verification failed";
            setError(message);
            onPaymentFailure?.(err);
          }
        },
        modal: {
          ondismiss: () => {
            setLoading(false);
            setError("Payment cancelled");
          },
        },
        theme: {
          color: "#2563eb", // Primary blue
        },
      };

      const checkout = new Razorpay(checkoutOptions);
      checkout.on("payment.failed", (response: any) => {
        setLoading(false);
        setError(
          response.error?.description || "Payment failed. Please try again."
        );
        onPaymentFailure?.(response.error);
      });

      checkout.open();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An error occurred";
      setError(message);
      onPaymentFailure?.(err);
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader title="Secure Checkout" subtitle="Powered by Razorpay" />
      <CardBody className="space-y-4 max-w-md">
        <div>
          <label className="block text-sm font-medium mb-1">Email *</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            className="w-full px-3 py-2 border border-[var(--border)] rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Full Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="John Doe"
            className="w-full px-3 py-2 border border-[var(--border)] rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Phone Number
          </label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+91 98765 43210"
            className="w-full px-3 py-2 border border-[var(--border)] rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        {amount && (
          <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md p-3">
            <p className="text-sm font-medium">
              Amount: <span className="text-lg">₹{amount.toLocaleString()}</span>
            </p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-md p-3">
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}

        <button
          onClick={handleCheckout}
          disabled={loading || !email}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          {loading ? "Processing..." : `Pay Now`}
        </button>

        <p className="text-xs text-[var(--muted-foreground)] text-center">
          Payments are secured with industry-standard encryption. We never store
          your card details.
        </p>
      </CardBody>
    </Card>
  );
}
