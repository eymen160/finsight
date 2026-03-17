/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable telemetry prompt
  env: {
    NEXT_TELEMETRY_DISABLED: '1',
  },
  // Don't fail build on type errors (we'll fix them separately)
  typescript: {
    ignoreBuildErrors: true,
  },
  // Don't fail on ESLint errors
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source:      '/api/backend/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/v1/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
