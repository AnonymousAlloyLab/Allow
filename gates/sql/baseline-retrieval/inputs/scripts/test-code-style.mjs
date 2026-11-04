import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { analyzeSource, collectSources, isExcludedDirectory } from './check-code-style.mjs';

/**
 * Produces a descriptive JSDoc block for fixture callables.
 * @param {string} parameters Optional complete parameter tag lines.
 * @returns {string} Documentation followed by a newline.
 */
function docs(parameters = '') {
  return `/**\n * Computes a bounded fixture result.\n${parameters} * @returns {number} Computed fixture result.\n */\n`;
}

/**
 * Builds a callable with an exact physical signature-to-body line count.
 * @param {number} count Required number of physical callable lines.
 * @returns {string} Documented independent fixture source.
 */
function physicalFixture(count) {
  return `${docs()}function measured() {\n${'\n'.repeat(count - 3)}return 1;\n}`;
}

/**
 * Requires a fixture to pass and inventories its expected callables.
 * @param {string} name Fixture filename used to select parser mode.
 * @param {string} source Independent fixture source text.
 * @param {number} expected Expected number of inventoried callables.
 * @returns {void} Throws an assertion failure when coverage differs.
 */
function expectPass(name, source, expected = 1) {
  const actual = analyzeSource(name, source);
  assert.deepEqual(actual.issues, [], `${name}: ${JSON.stringify(actual.issues)}`);
  assert.equal(actual.callables, expected, `${name}: callable coverage`);
}

/**
 * Requires a negative fixture to report a particular stable rule.
 * @param {string} name Fixture filename selecting the source language.
 * @param {string} source Independent fixture source text.
 * @param {string} rule Expected diagnostic rule identifier.
 * @returns {void} Throws an assertion failure if the checker misses it.
 */
function expectRule(name, source, rule) {
  const actual = analyzeSource(name, source);
  const rules = new Set();
  for (const issue of actual.issues) rules.add(issue.rule);
  assert.ok(rules.has(rule), `${name}: expected ${rule}, got ${JSON.stringify(actual.issues)}`);
}

/**
 * Checks physical-line boundaries and documentation tag requirements.
 * @returns {number} Number of independently asserted fixture cases.
 */
function testDocumentation() {
  expectPass('thirty.ts', physicalFixture(30));
  expectRule('thirty-one.ts', physicalFixture(31), 'method-length');
  expectRule('missing.js', 'function missing() { return 1; }', 'missing-doc');
  expectRule('summary.ts', '/** TODO */ function missing() { return 1; }', 'missing-doc');
  expectRule('param.ts', `${docs()}function missing(value: number) { return value; }`, 'param-doc');
  expectRule('return.ts', '/** Computes a fixture result. */ function missing() { return 1; }', 'return-doc');
  expectRule('parse.ts', 'function incomplete( {', 'parse-error');
  expectPass('arguments.ts', `${docs(' * @param {number} value Input fixture value.\n')}function identity(value: number) { return value; }`);
  return 8;
}

/**
 * Exercises constructors, accessors, callbacks and component function forms.
 * @returns {number} Number of independently asserted fixture cases.
 */
function testCallableForms() {
  expectPass('arrow.ts', `${docs()}const build = () => 1;`);
  expectPass('expression.js', `${docs()}const build = function compute() { return 1; };`);
  expectPass('component.tsx', `${docs()}function View() { return <div>Fixture</div>; }`);
  expectPass('constructor.ts', 'class Box {\n/** Constructs an empty fixture box. */ constructor() {} }');
  expectPass('getter.ts', `class Box {\n${docs()}get value() { return 1; } }`);
  expectPass('setter.ts', 'class Box {\n/** Sets the fixture value.\n * @param value New fixture value.\n */ set value(value: number) {} }');
  expectRule('constructor-missing.ts', 'class Box { constructor() {} }', 'missing-doc');
  expectRule('getter-missing.ts', 'class Box { get value() { return 1; } }', 'missing-doc');
  expectRule('callback.ts', 'values.map((value) => value);', 'unnamed-callback');
  expectRule('arrow-missing.ts', 'const value = () => 1;', 'missing-doc');
  expectPass('method.js', `const object = {\n${docs()}read() { return 1; } };`);
  expectPass('nested.ts', `${docs()}function outer() {\n${docs()}function inner() { return 1; }\nreturn inner();\n}`, 2);
  expectRule('abstract.ts', 'abstract class Shape { abstract size(): number; }', 'missing-doc');
  expectRule('overload.ts', 'function size(value: number): number;', 'missing-doc');
  expectRule('signature.ts', 'interface Callable { (): number; }', 'missing-doc');
  return 15;
}

/**
 * Exercises private fields, mutable aliases and constructor parameter state.
 * @returns {number} Number of independently asserted fixture cases.
 */
function testEncapsulation() {
  expectRule('public-field.ts', 'class State { values: number[] = []; }', 'public-mutable-field');
  expectRule('readonly-object.ts', 'class State { readonly values: number[] = []; }', 'public-mutable-field');
  expectRule('protected.ts', 'class State { protected values = []; }', 'public-mutable-field');
  expectRule('parameter-property.ts', 'class State {\n/** Initializes fixture state.\n * @param value Initial fixture list.\n */ constructor(public value: number[]) {} }', 'public-mutable-field');
  expectPass('private-field.ts', 'class State { private values: number[] = []; }', 0);
  expectPass('private-js.js', 'class State { #values = []; }', 0);
  expectPass('readonly-scalar.ts', 'class State { readonly count: number = 1; }', 0);
  return 7;
}

/**
 * Keeps generated Maven and runtime exclusions scoped to explicit root paths.
 * @returns {number} Number of independently asserted directory scope cases.
 */
function testExclusionScope() {
  assert.equal(isExcludedDirectory('backend/target'), true);
  assert.equal(isExcludedDirectory('.tools'), true);
  assert.equal(isExcludedDirectory('target'), false);
  assert.equal(isExcludedDirectory('frontend/target'), false);
  assert.equal(isExcludedDirectory('backend/src/target'), false);
  assert.equal(isExcludedDirectory('backend/target-authored'), false);
  assert.equal(isExcludedDirectory('tests/.tools'), false);
  assert.equal(isExcludedDirectory('tests'), false);
  assert.equal(isExcludedDirectory('frontend/node_modules'), true);
  assert.equal(isExcludedDirectory('frontend/dist'), true);
  assert.equal(isExcludedDirectory('formal/.lake'), true);
  assert.equal(isExcludedDirectory('frontend/src/generated'), false);
  assert.equal(isExcludedDirectory('scripts/build'), false);
  assert.equal(isExcludedDirectory('arbitraryfoo/vendor'), false);
  assert.equal(isExcludedDirectory('tests/node_modules'), false);
  assert.equal(isExcludedDirectory('gates/egraph/baseline-g1/inputs'), true);
  assert.equal(isExcludedDirectory('gates/egraph/formal-runs'), true);
  assert.equal(isExcludedDirectory('gates/retrieval/baseline-egraph/inputs'), true);
  assert.equal(isExcludedDirectory('gates/retrieval/formal-runs'), true);
  assert.equal(isExcludedDirectory('gates/egraph/engine'), false);
  assert.equal(isExcludedDirectory('frontend/src/formal-runs'), false);
  return 19;
}

/**
 * Confirms similarly named authored directories are actually traversed.
 * @returns {number} Number of source inventory assertions.
 */
function testAuthoredDirectoryTraversal() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'allow-style-scope-'));
  try {
    const names = ['frontend/src/generated', 'scripts/build', 'arbitraryfoo/vendor'];
    for (const name of names) {
      const target = path.join(directory, name);
      fs.mkdirSync(target, { recursive: true });
      fs.writeFileSync(path.join(target, 'authored.ts'), 'function undocumented() {}');
    }
    const files = [];
    collectSources(directory, files);
    assert.equal(files.length, names.length);
    for (const file of files) expectRule(file, fs.readFileSync(file, 'utf8'), 'missing-doc');
    return 4;
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

/**
 * Generates a documented Java method with an exact physical line count.
 * @param {number} count Required method length including signature and brace.
 * @returns {string} Independent Java fixture source.
 */
function javaPhysicalFixture(count) {
  return `class Fixture {\n/** Computes a fixture result.\n * @return computed result\n */\nint measured() {\n${'\n'.repeat(count - 3)}return 1;\n}\n}`;
}

/**
 * Checks one Java fixture against the actual pinned Checkstyle rules.
 * @param {string} jar Caller-selected official Checkstyle executable JAR.
 * @param {string} directory Temporary fixture directory outside the repository.
 * @param {string} source Independent Java source text to audit.
 * @param {string|null} rule Required failure marker or null for compliance.
 * @returns {void} Throws if the real Java audit disagrees with the fixture.
 */
function expectJava(jar, directory, source, rule) {
  const fixture = path.join(directory, 'Fixture.java');
  const config = fileURLToPath(new URL('../config/checkstyle.xml', import.meta.url));
  fs.writeFileSync(fixture, source);
  const result = spawnSync('java', ['-jar', jar, '-c', config, fixture], { encoding: 'utf8', timeout: 15000 });
  assert.ifError(result.error);
  const output = `${result.stdout}${result.stderr}`;
  if (rule) {
    assert.notEqual(result.status, 0, output);
    assert.ok(output.includes(rule), `Missing Java rule ${rule}: ${output}`);
  } else assert.equal(result.status, 0, output);
}

/**
 * Exercises real Java method, constructor, field and callback enforcement.
 * @param {string} jar Official pinned Checkstyle executable JAR path.
 * @param {string} directory Temporary fixture directory outside the repository.
 * @returns {number} Number of independently asserted Java audit cases.
 */
function testJavaCases(jar, directory) {
  expectJava(jar, directory, javaPhysicalFixture(30), null);
  expectJava(jar, directory, javaPhysicalFixture(31), 'MethodLength');
  expectJava(jar, directory, 'class Fixture { private void missing() {} }', 'MissingJavadocMethod');
  expectJava(jar, directory, 'class Fixture { Fixture() {} }', 'MissingJavadocMethod');
  expectJava(jar, directory, 'record Fixture(int value) { Fixture {} }', 'MissingJavadocMethod');
  expectJava(jar, directory, 'class Fixture { public int mutable; }', 'VisibilityModifier');
  expectJava(jar, directory, 'class Fixture { public static final Object MUTABLE = new Object(); }', 'MatchXpath');
  expectJava(jar, directory, 'class Fixture { /** Executes a fixture callback. */ void run() { Runnable task = () -> {}; } }', 'MatchXpath');
  expectJava(jar, directory, 'class Fixture {\n/** Selects a fixture value.\n * @return selected result\n */\nint read() { return switch (1) { case 1 -> 2; default -> 0; }; } }', null);
  expectJava(jar, directory, 'class Fixture {\n/** Copies a fixture input.\n * @return copied input\n */\nint copy(int value) { return value; } }', 'JavadocMethod');
  expectJava(jar, directory, 'class Fixture {\n/** Computes a fixture value. */\nint compute() { return 1; } }', 'JavadocMethod');
  expectJava(jar, directory, 'class Fixture {\n/** Copies a fixture value.\n * @return copied result\n */ int copy(int value) { return value; } }', 'RegexpSinglelineJava');
  expectJava(jar, directory, 'class Fixture { void broken( }', 'Exception');
  return 13;
}

/**
 * Runs optional Java fixtures and always removes temporary source files.
 * @returns {number} Number of real Java fixtures run, or zero without a JAR.
 */
function testJava() {
  const jar = process.env.ALLOW_CHECKSTYLE_JAR;
  if (!jar) return 0;
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'allow-style-'));
  try {
    return testJavaCases(jar, directory);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

const count = testDocumentation() + testCallableForms() + testEncapsulation()
  + testExclusionScope() + testAuthoredDirectoryTraversal();
const javaCount = testJava();
console.log(`Style checker self-tests: ${count} JS/TS cases and ${javaCount} Java cases passed.`);
