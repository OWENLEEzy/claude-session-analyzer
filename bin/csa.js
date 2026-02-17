#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Run as a module to support relative imports
const args = ['-m', 'analyzer.cli', ...process.argv.slice(2)];

// Run Python with the package directory in PYTHONPATH
const python = spawn('python3', args, {
  stdio: 'inherit',
  cwd: path.join(__dirname, '..'),
  env: { ...process.env, PYTHONPATH: path.join(__dirname, '..') }
});

python.on('close', (code) => {
  process.exit(code || 0);
});
