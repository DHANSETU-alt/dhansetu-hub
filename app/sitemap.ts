import { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://dhansetuhub.in';
  const routes = ['', '/tools', '/tools/image-to-pdf', '/smartbudget', '/tax-estimator', '/gst', '/tools/invoice', '/resume-ai', '/pdf-studio', '/peopledesk', '/partners', '/join-as-expert', '/affiliate', '/privacy', '/terms'];

  return routes.map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'weekly',
    priority: route === '' ? 1 : 0.8,
  }));
}
