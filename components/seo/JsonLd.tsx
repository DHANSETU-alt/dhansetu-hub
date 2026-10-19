export function JsonLd() {
  const data = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: 'Dhansetu Hub',
    description: 'Browser-based tools for money clarity and everyday work.',
    brand: { '@type': 'Brand', name: 'Dhansetu Hub' },
    offers: [
      { '@type': 'Offer', name: 'SmartBudget Pro', price: '149', priceCurrency: 'INR', availability: 'https://schema.org/InStock', url: 'https://dhansetuhub.in/checkout?tier=smartbudget_pro' },
      { '@type': 'Offer', name: 'DhanSetu All Access', price: '399', priceCurrency: 'INR', availability: 'https://schema.org/InStock', url: 'https://dhansetuhub.in/checkout?tier=all_access' },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
