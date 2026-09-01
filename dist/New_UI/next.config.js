let userConfig = undefined;
try {
  userConfig = require('./v0-user-next.config');
} catch (e) {
  // ignore error
}

function mergeConfig(nextConfig, userConfig) {
  if (!userConfig) {
    return nextConfig;
  }

  for (const key in userConfig) {
    if (
      typeof nextConfig[key] === 'object' &&
      !Array.isArray(nextConfig[key])
    ) {
      nextConfig[key] = {
        ...nextConfig[key],
        ...userConfig[key],
      };
    } else {
      nextConfig[key] = userConfig[key];
    }
  }
  
  return nextConfig;
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  experimental: {
    webpackBuildWorker: true,
    parallelServerBuildTraces: true,
    parallelServerCompiles: true
  },
  webpack: (config, { isServer }) => {
    // Only include optional features if they're installed
    const optionalFeatures = ['recharts', 'embla-carousel-react', 'vaul', 'cmdk'];

    optionalFeatures.forEach(feature => {
      try {
        require.resolve(feature);
        console.log(`Feature ${feature} is available`);
      } catch (e) {
        console.log(`Feature ${feature} is not installed, excluding from bundle`);
        // For Next.js, we should use a different approach for externals
        if (isServer) {
          config.externals = config.externals || [];
          if (Array.isArray(config.externals)) {
            config.externals.push(feature);
          } else {
            config.externals = [config.externals, feature];
          }
        }
      }
    });

    return config;
  }
};

module.exports = mergeConfig(nextConfig, userConfig);
