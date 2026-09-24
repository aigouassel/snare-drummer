import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/**
 * A GitHub Page for a project repository is served from /<repo>/, not from
 * the root, so every asset URL in the built page has to carry that prefix.
 * Only when building: the dev server keeps serving from / , which is what the
 * `yarn dev` in everyone's muscle memory expects.
 */
const BASE = '/snare-drummer/'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? BASE : '/',
  plugins: [react()],
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
}))
