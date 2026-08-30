/**
 * apps/mobile/metro.config.js
 *
 * Metro configuration for Monorepo with Expo Router.
 */

const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// Preserve Expo's defaults and add the workspace root for local packages.
config.watchFolders = [...new Set([...(config.watchFolders || []), monorepoRoot])];

// Let Metro know where to resolve workspace packages and in what order.
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(monorepoRoot, 'node_modules'),
];

module.exports = config;
