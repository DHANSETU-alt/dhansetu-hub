'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';

export default function PartnerNetworkPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [partnerEmail, setPartnerEmail] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    website: '',
    tier: 'affiliate',
  });

  return (
    <div className="space-y-8 p-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold tracking-tight">Partner Network</h1>
        <p className="text-lg text-gray-600 mt-2">
          Earn commissions by referring customers. 15-25% per sale, paid monthly.
        </p>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="apply">Apply Now</TabsTrigger>
          <TabsTrigger value="resources">Resources</TabsTrigger>
        </TabsList>

        {/* Partner Dashboard Tab */}
        <TabsContent value="dashboard" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Partner Dashboard</CardTitle>
              <CardDescription>
                View your referrals, commissions, and payouts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Partner Email</label>
                <Input
                  placeholder="your@email.com"
                  value={partnerEmail}
                  onChange={(e) => setPartnerEmail(e.target.value)}
                  className="mt-1"
                />
              </div>

              {partnerEmail && (
                <div className="space-y-6">
                  {/* Stats Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Card className="bg-blue-50">
                      <CardContent className="pt-4">
                        <div className="text-3xl font-bold">0</div>
                        <p className="text-sm text-gray-600">Total Clicks</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-green-50">
                      <CardContent className="pt-4">
                        <div className="text-3xl font-bold">0</div>
                        <p className="text-sm text-gray-600">Conversions</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-purple-50">
                      <CardContent className="pt-4">
                        <div className="text-3xl font-bold">₹0</div>
                        <p className="text-sm text-gray-600">Revenue</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-50">
                      <CardContent className="pt-4">
                        <div className="text-3xl font-bold">₹0</div>
                        <p className="text-sm text-gray-600">Pending Commission</p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Tabs for Dashboard Content */}
                  <Tabs defaultValue="referral" className="w-full">
                    <TabsList>
                      <TabsTrigger value="referral">Referral Link</TabsTrigger>
                      <TabsTrigger value="commissions">Commissions</TabsTrigger>
                      <TabsTrigger value="payouts">Payouts</TabsTrigger>
                    </TabsList>

                    {/* Referral Link */}
                    <TabsContent value="referral" className="space-y-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Your Referral Link</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <label className="text-sm font-medium">Unique Referral Link</label>
                            <div className="flex gap-2 mt-2">
                              <Input
                                readOnly
                                value="https://app.example.com?partner_id=xxx"
                                className="bg-gray-50"
                              />
                              <Button variant="outline">Copy</Button>
                            </div>
                          </div>
                          <div className="border-t pt-4 space-y-2">
                            <p className="text-sm font-medium">Share on</p>
                            <div className="flex gap-2">
                              <Button variant="outline" size="sm">Twitter</Button>
                              <Button variant="outline" size="sm">LinkedIn</Button>
                              <Button variant="outline" size="sm">WhatsApp</Button>
                              <Button variant="outline" size="sm">Email</Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    {/* Commissions */}
                    <TabsContent value="commissions" className="space-y-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Commission History</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-center py-8 text-gray-600">
                            <p>No commissions yet. Share your referral link to start earning!</p>
                          </div>
                          <div className="overflow-x-auto mt-4 hidden">
                            <table className="w-full text-sm">
                              <thead className="border-b">
                                <tr>
                                  <th className="text-left py-2">Date</th>
                                  <th className="text-left py-2">Customer</th>
                                  <th className="text-left py-2">Sale Amount</th>
                                  <th className="text-left py-2">Commission</th>
                                  <th className="text-left py-2">Status</th>
                                </tr>
                              </thead>
                              <tbody>
                                {/* Empty state */}
                              </tbody>
                            </table>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    {/* Payouts */}
                    <TabsContent value="payouts" className="space-y-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Payout Requests</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Button className="w-full">Request Payout</Button>
                          <div className="text-center py-8 text-gray-600">
                            <p>No payout requests yet. Minimum payout: ₹100</p>
                          </div>
                          <div className="overflow-x-auto mt-4 hidden">
                            <table className="w-full text-sm">
                              <thead className="border-b">
                                <tr>
                                  <th className="text-left py-2">Date</th>
                                  <th className="text-left py-2">Amount</th>
                                  <th className="text-left py-2">Status</th>
                                  <th className="text-left py-2">Method</th>
                                </tr>
                              </thead>
                              <tbody>
                                {/* Empty state */}
                              </tbody>
                            </table>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>
                  </Tabs>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Apply Tab */}
        <TabsContent value="apply" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Become a Partner</CardTitle>
              <CardDescription>
                Join our partner network and start earning commissions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Tier Selection */}
              <div>
                <label className="text-sm font-medium mb-3 block">Select Your Tier</label>
                <div className="grid md:grid-cols-3 gap-4">
                  {[
                    {
                      tier: 'affiliate',
                      title: 'Affiliate',
                      rate: '15%',
                      features: ['Per-sale commission', 'Basic dashboard'],
                    },
                    {
                      tier: 'reseller',
                      title: 'Reseller',
                      rate: '20%',
                      features: ['Per-sale commission', 'Bulk discounts', 'Performance dashboard'],
                    },
                    {
                      tier: 'agency',
                      title: 'Agency',
                      rate: '25%',
                      features: ['Per-sale commission', 'Priority support', 'Advanced analytics'],
                    },
                  ].map((t) => (
                    <Card
                      key={t.tier}
                      className={`cursor-pointer transition-all ${
                        formData.tier === t.tier ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                      }`}
                      onClick={() => setFormData({ ...formData, tier: t.tier })}
                    >
                      <CardContent className="pt-6">
                        <h3 className="font-bold text-lg">{t.title}</h3>
                        <p className="text-2xl font-bold text-green-600 my-2">{t.rate}</p>
                        <ul className="text-sm space-y-1">
                          {t.features.map((f) => (
                            <li key={f} className="text-gray-600">✓ {f}</li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>

              {/* Application Form */}
              <div className="space-y-4 border-t pt-6">
                <div>
                  <label className="text-sm font-medium">Name *</label>
                  <Input
                    placeholder="Your full name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-1"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium">Email *</label>
                  <Input
                    type="email"
                    placeholder="your@email.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="mt-1"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium">Phone</label>
                  <Input
                    placeholder="+91 98765 43210"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="mt-1"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium">Company</label>
                  <Input
                    placeholder="Your company name"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    className="mt-1"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium">Website</label>
                  <Input
                    placeholder="https://yourcompany.com"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    className="mt-1"
                  />
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
                  <p className="font-medium text-blue-900">Next Steps</p>
                  <ul className="mt-2 space-y-1 text-blue-800">
                    <li>✓ Submit your application</li>
                    <li>✓ Founder reviews and approves</li>
                    <li>✓ Receive your unique referral link</li>
                    <li>✓ Start sharing and earning commissions</li>
                  </ul>
                </div>

                <Button className="w-full" size="lg">Submit Application</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Resources Tab */}
        <TabsContent value="resources" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Partner Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <Card className="bg-gray-50">
                  <CardContent className="pt-4">
                    <h3 className="font-bold mb-2">📋 Commission Guide</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Understand how commissions are calculated and when they're paid out.
                    </p>
                    <Button variant="link" className="p-0">Learn more →</Button>
                  </CardContent>
                </Card>

                <Card className="bg-gray-50">
                  <CardContent className="pt-4">
                    <h3 className="font-bold mb-2">📱 Marketing Materials</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Download templates, copy, and graphics for your referral campaigns.
                    </p>
                    <Button variant="link" className="p-0">Browse assets →</Button>
                  </CardContent>
                </Card>

                <Card className="bg-gray-50">
                  <CardContent className="pt-4">
                    <h3 className="font-bold mb-2">📊 Analytics Deep Dive</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Learn how to interpret your stats and optimize your referrals.
                    </p>
                    <Button variant="link" className="p-0">View guide →</Button>
                  </CardContent>
                </Card>

                <Card className="bg-gray-50">
                  <CardContent className="pt-4">
                    <h3 className="font-bold mb-2">💬 Support & FAQ</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Got questions? We're here to help. Check our FAQ or contact support.
                    </p>
                    <Button variant="link" className="p-0">Get help →</Button>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
