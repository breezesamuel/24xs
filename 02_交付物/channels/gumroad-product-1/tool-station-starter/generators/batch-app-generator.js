// batch-app-generator.js - real batch HTML-app factory
// Reads  projects.txt  (one slug per line, max 3000)
// Reads  template.html (ASCII skeleton with {{NAME}} and {{STORE}})
// Writes out/<slug>.html for every line -> double-click verifiable.
// Usage: node batch-app-generator.js   then open C:\bingdashan\out\
"use strict";
var fs = require("fs");
var path = require("path");

var CWD = process.cwd();
var LIST = path.join(CWD, "projects.txt");
var TPL  = path.join(CWD, "template.html");
var OUT  = path.join(CWD, "out");
var MAX  = 3000;

if (!fs.existsSync(LIST)) { console.log("ERR missing projects.txt"); process.exit(1); }
if (!fs.existsSync(TPL))  { console.log("ERR missing template.html"); process.exit(1); }
if (!fs.existsSync(OUT))  { fs.mkdirSync(OUT); }

var tpl = fs.readFileSync(TPL, "utf8");
var lines = fs.readFileSync(LIST, "utf8")
  .split(/\r?\n/)
  .map(function (s) { return s.trim(); })
  .filter(function (s) { return s.length > 0; });

if (lines.length > MAX) { lines = lines.slice(0, MAX); }

var made = 0;
lines.forEach(function (slug) {
  if (!/^[a-z0-9-]{2,40}$/.test(slug)) { console.log("SKIP bad slug: " + slug); return; }
  var html = tpl
    .replace(/{{NAME}}/g, slug.replace(/-/g, " "))
    .replace(/{{STORE}}/g, slug)
    .replace(/{{SLUG}}/g, slug);
  var f = path.join(OUT, slug + ".html");
  fs.writeFileSync(f, html, "utf8");
  made++;
});

console.log("made=" + made + " apps -> " + OUT);
