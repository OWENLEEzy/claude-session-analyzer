#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Path to Python CLI
const cliPath = path.join(__dirname, '..', 'analyzer', 'cli.py');

// Forward all arguments to Python CLI
const args = [cliPath, ...process.argv.slice(2)];

// Run Python
const python = spawn('python3', args, {
  stdio: 'inherit',
  env: { ...process.env, PYTHONPATH: path.join(__dirname, '..') }
});

python.on('close', (code) => {
  process.exit(code || 0);
});
