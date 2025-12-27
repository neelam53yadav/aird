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
