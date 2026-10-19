#!/usr/bin/env node

const session = process.env.BSK_SESSION;
if (!session) {
  console.error("Set BSK_SESSION to an active browser-skill session.");
  process.exit(2);
}

const { execFileSync } = require("node:child_process");
const expression = `JSON.stringify((() => { const cards = [...document.querySelectorAll('[data-testid="service-card"]')]; const buttons = cards.flatMap(card => [...card.querySelectorAll('a,button')].map(control => ({ text: control.textContent.trim(), clipped: control.scrollWidth > control.clientWidth || control.scrollHeight > control.clientHeight }))); return { cardCount: cards.length, buttons, pass: cards.length === 5 && buttons.length === 5 && buttons.every(button => button.text && !button.clipped) }; })())`;
const output = execFileSync("bsk", ["evaluate", "--session", session, expression], { encoding: "utf8" }).trim();
const result = JSON.parse(output.split("\n").at(-1));
console.log(JSON.stringify(result, null, 2));
if (!result.pass) process.exit(1);
