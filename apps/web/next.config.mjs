/** @type {import('next').NextConfig} */
const backendBaseUrl = (process.env.API_URL || 'http://127.0.0.1:8000')
  .replace(/\/+$/, '')
  .replace(/\/api$/, '');

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@medical/shared', '@medical/api-client'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // Preserve the original API path even when API_URL is configured.
        // API_URL may be either http://host:port or http://host:port/api.
        destination: `${backendBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
