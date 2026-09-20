import { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://dhansetuhub.in';
  const routes = ['', '/smartbudget', '/tools/invoice', '/resume-ai', '/pdf-studio', '/peopledesk', '/privacy', '/terms'];

  return routes.map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'weekly',
    priority: route === '' ? 1 : 0.8,
  }));
}
