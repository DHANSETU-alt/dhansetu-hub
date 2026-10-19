#!/usr/bin/env node
const { execFileSync } = require("node:child_process");

const session = process.env.BSK_SESSION;
if (!session) {
  console.error("Set BSK_SESSION to an active browser-skill session.");
  process.exit(2);
}

const expression = `JSON.stringify((() => {
  const cards = [...document.querySelectorAll('[data-testid="service-card"]')];
  const buttons = cards.map(card => {
    const control = card.querySelector('a,button');
    return { text: control?.textContent.trim() || '', clipped: !control || control.scrollWidth > control.clientWidth || control.scrollHeight > control.clientHeight };
  });
  const modal = !!document.querySelector('[role="dialog"]');
  const signIn = [...document.querySelectorAll('button')].some(button => button.textContent.trim() === 'Sign in');
  return { cardCount: cards.length, buttons, signIn, modal, pass: cards.length === 5 && buttons.every(button => button.text && !button.clipped) };
})())`;

const output = execFileSync("bsk", ["evaluate", "--session", session, expression], { encoding: "utf8" }).trim();
const result = JSON.parse(output.split("\n").at(-1));
console.log(JSON.stringify(result, null, 2));
if (!result.pass) process.exit(1);
