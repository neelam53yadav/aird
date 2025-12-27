/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['localhost'],
  },
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000',
  },
  webpack: (config, { isServer }) => {
    // Ensure path aliases work correctly for both client and server
    const alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, '.'),
    }
    config.resolve.alias = alias
    
    // Ensure modules are resolved correctly
    config.resolve.modules = [
      path.resolve(__dirname, '.'),
      ...(config.resolve.modules || []),
    ]
    
    // Ensure extensions are resolved
    config.resolve.extensions = [
      '.tsx',
      '.ts',
      '.jsx',
      '.js',
      ...(config.resolve.extensions || []),
    ]
    
    return config
  },
}

module.exports = nextConfig
