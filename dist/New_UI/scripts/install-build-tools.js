const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('Installing build tools...');

const buildTools = [
    'next',
    'typescript',
    '@types/node',
    '@types/react',
    '@types/react-dom', 
    '@types/jszip',
    'tailwindcss',
    'postcss',
    'autoprefixer'
];

try {
    execSync(`npm install --save-dev --legacy-peer-deps ${buildTools.join(' ')}`, { stdio: 'inherit' });
    console.log('Build tools installed successfully');
} catch (error) {
    console.error('Failed to install build tools:', error);
    process.exit(1);
}


