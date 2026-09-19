export function JsonLd() {
  const data = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Dhansetu Hub Lifetime Pass',
    operatingSystem: 'Web/Windows/Android',
    applicationCategory: 'Productivity / Finance',
    offers: {
      '@type': 'Offer',
      price: '99.00',
      priceCurrency: 'INR',
      availability: 'https://schema.org/InStock',
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
