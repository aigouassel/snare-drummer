import { defineConfig } from 'vitest/config'

/**
 * One run over every workspace, so `yarn test` covers the whole repository.
 * Each project brings its own config: the data packages run in Node with no
 * DOM, and the app's comes from its Vite config.
 */
export default defineConfig({
  test: { projects: ['packages/*', 'apps/web'] },
})
