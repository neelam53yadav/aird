/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['localhost'],
  },
  env: {
    // API URL is now centralized in lib/config.ts
    // Keep NEXT_PUBLIC_API_BASE for build-time environment variable injection if needed
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE,
  },
  webpack: (config) => {
    // Ensure path aliases work correctly
    if (!config.resolve) {
      config.resolve = {}
    }
    if (!config.resolve.alias) {
      config.resolve.alias = {}
    }
    
    // Set the @ alias to the project root
    config.resolve.alias['@'] = path.resolve(__dirname, '.')
    
    return config
  },
}

module.exports = nextConfig
