const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const featureDeps = {
    'charts': ['recharts'],
    'carousel': ['embla-carousel-react'],
    'otp': ['input-otp'],
    'drawer': ['vaul'],
    'command-palette': ['cmdk']
};

const feature = process.argv[2];

if (!feature) {
    console.error('Usage: node install-feature.js <feature-name>');
    console.error('Available features:', Object.keys(featureDeps).join(', '));
    process.exit(1);
}

if (!featureDeps[feature]) {
    console.error(`Unknown feature: ${feature}`);
    console.error('Available features:', Object.keys(featureDeps).join(', '));
    process.exit(1);
}

console.log(`Installing dependencies for feature: ${feature}`);

try {
    const deps = featureDeps[feature];
    execSync(`npm install ${deps.join(' ')}`, { stdio: 'inherit' });
    console.log(`Feature ${feature} installed successfully`);
} catch (error) {
    console.error(`Failed to install feature ${feature}:`, error);
    process.exit(1);
}