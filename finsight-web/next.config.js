/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source:      '/api/backend/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/v1/:path*`,
      },
    ]
  },
  async headers() {
    return [
      {
        source: '/api/chat/stream',
        headers: [
          { key: 'Cache-Control',     value: 'no-cache, no-store' },
          { key: 'X-Accel-Buffering', value: 'no' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
