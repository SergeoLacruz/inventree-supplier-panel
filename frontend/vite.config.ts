import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteExternalsPlugin } from 'vite-plugin-externals';
import { lingui } from '@lingui/vite-plugin';

/**
 * The following libraries are externalized to avoid bundling them with the plugin.
 * These libraries are expected to be provided by the InvenTree core application.
 */
export const externalLibs: Record<string, string> = {
  react: 'React',
  'react-dom': 'ReactDOM',
  ReactDom: 'ReactDOM',
  '@lingui/core': 'LinguiCore',
  '@lingui/react': 'LinguiReact',
  '@mantine/core': 'MantineCore',
  '@mantine/notifications': 'MantineNotifications'
};

// Just the keys of the externalLibs object
const externalKeys = Object.keys(externalLibs);

/**
 * Vite config to build the frontend plugin as an exported module.
 * This will be distributed in the 'static' directory of the plugin.
 */
export default defineConfig({
  plugins: [
    lingui(),
    react({
      jsxRuntime: 'classic',
      babel: {
        plugins: ['macros'] // Required for @lingui macros
      }
    }),
    viteExternalsPlugin(externalLibs)
  ],
  esbuild: {
    jsx: 'preserve'
  },
  build: {
    // minify: false,
    target: 'esnext',
    cssCodeSplit: false,
    manifest: true,
    sourcemap: true,
    rollupOptions: {
      preserveEntrySignatures: 'exports-only',
      input: {
        Panel: './src/Panel.tsx',
        AddSupplierPartPanel: './src/AddSupplierPartPanel.ts',
        Settings: './src/Settings.tsx'
      },
      output: [
        // Generate two sets of output files:
        // One without hashes - for backwards compatibility
        {
          dir: '../inventree_supplier_panel/static',
          entryFileNames: '[name].js',
          assetFileNames: 'assets/[name].[ext]',
          globals: externalLibs
        },
        // And one with hashes for cache busting
        {
          dir: '../inventree_supplier_panel/static',
          entryFileNames: '[name]-[hash].js',
          assetFileNames: 'assets/[name].[ext]',
          globals: externalLibs
        }
      ],
      external: externalKeys
    }
  },
  optimizeDeps: {
    exclude: externalKeys
  }
});
