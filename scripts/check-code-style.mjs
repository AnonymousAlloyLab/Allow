import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EXCLUDED_PATHS = new Set(['.git', '.tools', 'backend/target',
  'frontend/node_modules', 'frontend/dist', 'formal/.lake',
  'gates/egraph/baseline-g1/inputs', 'gates/egraph/formal-runs',
  'gates/retrieval/baseline-egraph/inputs', 'gates/retrieval/formal-runs',
  'gates/sql/baseline-retrieval/inputs', 'gates/sql/baseline-r3/inputs',
  'gates/sql/formal-runs', 'gates/document/baseline-sql/inputs',
  'gates/document/draft-runs',
  'gates/sql/immutable-image-candidate/completion-runs',
  'gates/sql/immutable-image-candidate/integration-runs',
  'gates/document/validation-context-candidate/formal-runs',
  'gates/document/validation-context-candidate/runtime-closure/runs/final-v1/inputs/backend/target',
  'gates/document/validation-context-candidate/runtime-closure/runs/final-v2/inputs/backend/target',
  'gates/document/validation-context-candidate/runtime-runs/current-v1/binding-v1/inputs/backend/target',
  'gates/performance/fresh-tier1-candidate/implementation/build-r1/backend/target',
  'gates/performance/fresh-tier1-candidate/implementation/build-r2/backend/target']);
const EXTENSIONS = /\.(?:[cm]?[jt]s|[jt]sx)$/i;

/**
 * Recognizes explicit dependency and generated-output directory exclusions.
 * @param {string} relativePath Directory path relative to the repository root.
 * @returns {boolean} Whether this exact directory is outside authored scans.
 */
export function isExcludedDirectory(relativePath) {
  const normalized = path.normalize(relativePath).split(path.sep).join('/');
  return EXCLUDED_PATHS.has(normalized);
}

/**
 * Describes a source violation at its exact physical line.
 * @param {object} context Parsed source and accumulated failures.
 * @param {object} node Syntax node responsible for the violation.
 * @param {string} rule Stable diagnostic rule name.
 * @param {string} message Actionable failure description.
 * @returns {void} Appends one diagnostic to the supplied result.
 */
function report(context, node, rule, message) {
  const position = context.source.getLineAndCharacterOfPosition(node.getStart(context.source));
  context.issues.push({ file: context.source.fileName, line: position.line + 1, rule, message });
}

/**
 * Recognizes executable callables and explicit interface method declarations.
 * @param {object} node TypeScript syntax node to classify.
 * @returns {boolean} Whether documentation and physical length apply.
 */
function isCallable(node) {
  return ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node)
    || ts.isArrowFunction(node) || ts.isMethodDeclaration(node)
    || ts.isMethodSignature(node) || ts.isConstructorDeclaration(node)
    || ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)
    || ts.isCallSignatureDeclaration(node) || ts.isConstructSignatureDeclaration(node);
}

/**
 * Finds the declaration owning documentation for an assigned callable.
 * @param {object} node Callable syntax node being checked.
 * @returns {object} Declaration that carries the callable's JSDoc.
 */
function documentationOwner(node) {
  let owner = node;
  while (owner.parent && (ts.isVariableDeclaration(owner.parent)
      || ts.isVariableDeclarationList(owner.parent) || ts.isVariableStatement(owner.parent)
      || ts.isPropertyAssignment(owner.parent) || ts.isPropertyDeclaration(owner.parent)
      || ts.isParenthesizedExpression(owner.parent))) {
    owner = owner.parent;
  }
  return owner;
}

/**
 * Extracts readable text from plain or structured JSDoc comments.
 * @param {unknown} comment Parsed TypeScript JSDoc comment value.
 * @returns {string} Flattened text without syntax-node serialization.
 */
function commentText(comment) {
  return ts.getTextOfJSDocComment(comment) || '';
}

/**
 * Rejects empty and obvious placeholder documentation descriptions.
 * @param {string} value Documentation prose to inspect.
 * @returns {boolean} Whether prose is suitable for further human review.
 */
function meaningful(value) {
  const text = value.trim();
  return text.length >= 4 && !/^(?:todo|tbd|description|parameter|returns?|result|none|n\/a)[.!]?$/i.test(text);
}

/**
 * Resolves a nonempty JSDoc block attached to the callable declaration.
 * @param {object} node Callable syntax node being inspected.
 * @returns {object|undefined} Attached documentation block when present.
 */
function documentation(node) {
  const owner = documentationOwner(node);
  return node.jsDoc?.at(-1) || owner.jsDoc?.at(-1);
}

/**
 * Checks callable documentation tags against its actual parameter list.
 * @param {object} context Parsed source and accumulated failures.
 * @param {object} node Callable syntax node being inspected.
 * @param {object} doc Attached JSDoc block with summary and tags.
 * @returns {void} Appends missing or incomplete tag diagnostics.
 */
function checkTags(context, node, doc) {
  const tags = Array.from(doc.tags || []);
  const parameters = tags.filter(isParameterTag);
  for (let index = 0; index < node.parameters.length; index += 1) {
    const parameter = node.parameters[index];
    const name = ts.isIdentifier(parameter.name) ? parameter.name.text : null;
    const tag = name ? parameters.find(matchesParameter.bind(null, name)) : parameters[index];
    if (!tag || !meaningful(commentText(tag.comment))) {
      report(context, parameter, 'param-doc', `Document parameter ${name || index + 1} with a description.`);
    }
  }
  if (!ts.isConstructorDeclaration(node) && !ts.isConstructSignatureDeclaration(node)
      && !ts.isSetAccessorDeclaration(node)) {
    const tag = tags.find(isReturnTag);
    if (!tag || !meaningful(commentText(tag.comment))) {
      report(context, node, 'return-doc', 'Document the result or void side effects with @returns.');
    }
  }
}

/**
 * Recognizes a JSDoc parameter tag by compiler syntax kind.
 * @param {object} tag Candidate JSDoc tag.
 * @returns {boolean} Whether this is a parameter description.
 */
function isParameterTag(tag) {
  return ts.isJSDocParameterTag(tag);
}

/**
 * Matches an actual argument name against its JSDoc parameter tag.
 * @param {string} name Declared argument name to match.
 * @param {object} tag Candidate JSDoc parameter tag.
 * @returns {boolean} Whether the tag names this argument.
 */
function matchesParameter(name, tag) {
  return tag.name.getText() === name;
}

/**
 * Recognizes either supported spelling of a JSDoc return tag.
 * @param {object} tag Candidate JSDoc tag.
 * @returns {boolean} Whether this tag describes a function result.
 */
function isReturnTag(tag) {
  return ts.isJSDocReturnTag(tag);
}

/**
 * Checks one callable's physical length, naming and documentation.
 * @param {object} context Parsed source and accumulated failures.
 * @param {object} node Callable syntax node being inspected.
 * @returns {void} Records the callable and any style violations.
 */
function checkCallable(context, node) {
  const owner = documentationOwner(node);
  const start = context.source.getLineAndCharacterOfPosition(owner.getStart(context.source)).line;
  const end = context.source.getLineAndCharacterOfPosition(node.end - 1).line;
  context.callables += 1;
  if (end - start + 1 > 30) report(context, node, 'method-length', `Callable spans ${end - start + 1} physical lines; maximum is 30.`);
  if ((ts.isArrowFunction(node) || ts.isFunctionExpression(node)) && owner === node && !node.name) {
    report(context, node, 'unnamed-callback', 'Use a named documented function for callbacks.');
  }
  const doc = documentation(node);
  if (!doc || !meaningful(commentText(doc.comment))) {
    report(context, node, 'missing-doc', 'Provide meaningful JSDoc summary, parameters and result documentation.');
    return;
  }
  checkTags(context, node, doc);
}

/**
 * Classifies primitive readonly state that cannot expose mutable objects.
 * @param {object} node Class field or parameter property declaration.
 * @returns {boolean} Whether the declaration is a readonly scalar value.
 */
function immutableScalar(node) {
  if (!hasModifier(node, ts.SyntaxKind.ReadonlyKeyword)) return false;
  const primitive = new Set([ts.SyntaxKind.StringKeyword, ts.SyntaxKind.NumberKeyword,
    ts.SyntaxKind.BooleanKeyword, ts.SyntaxKind.BigIntKeyword, ts.SyntaxKind.SymbolKeyword]);
  if (node.type && primitive.has(node.type.kind)) return true;
  return Boolean(node.initializer && (ts.isStringLiteral(node.initializer)
    || ts.isNumericLiteral(node.initializer) || node.initializer.kind === ts.SyntaxKind.TrueKeyword
    || node.initializer.kind === ts.SyntaxKind.FalseKeyword));
}

/**
 * Looks up a modifier without relying on source text matching.
 * @param {object} node Declaration with optional compiler modifiers.
 * @param {number} kind Compiler syntax kind to locate.
 * @returns {boolean} Whether the modifier occurs on this declaration.
 */
function hasModifier(node, kind) {
  for (const modifier of node.modifiers || []) if (modifier.kind === kind) return true;
  return false;
}

/**
 * Enforces private mutable state for class fields and parameter properties.
 * @param {object} context Parsed source and accumulated failures.
 * @param {object} node Class field or constructor argument syntax node.
 * @returns {void} Records an exposed mutable-state violation if applicable.
 */
function checkField(context, node) {
  const parameterProperty = ts.isParameter(node) && ts.isConstructorDeclaration(node.parent)
    && Boolean(node.modifiers?.length);
  if (!ts.isPropertyDeclaration(node) && !parameterProperty) return;
  if (ts.isPrivateIdentifier(node.name) || hasModifier(node, ts.SyntaxKind.PrivateKeyword)) return;
  if (!immutableScalar(node)) report(context, node, 'public-mutable-field', 'Keep mutable class state private; readonly scalars are allowed.');
}

/**
 * Visits every syntax node including nested callbacks and test functions.
 * @param {object} context Parsed source and accumulated failures.
 * @param {object} node Current compiler syntax node.
 * @returns {void} Accumulates callable inventory and field diagnostics.
 */
function visit(context, node) {
  if (isCallable(node)) checkCallable(context, node);
  checkField(context, node);
  ts.forEachChild(node, visit.bind(null, context));
}

/**
 * Parses and checks one authored JavaScript or TypeScript source string.
 * @param {string} filename Source filename selecting JS, TS or TSX parsing.
 * @param {string} text Exact source bytes decoded as UTF-8.
 * @returns {object} Diagnostics and total discovered callable count.
 */
export function analyzeSource(filename, text) {
  const source = ts.createSourceFile(filename, text, ts.ScriptTarget.Latest, true);
  const context = { source, issues: [], callables: 0 };
  for (const diagnostic of source.parseDiagnostics) {
    const line = source.getLineAndCharacterOfPosition(diagnostic.start || 0).line + 1;
    context.issues.push({ file: filename, line, rule: 'parse-error',
      message: ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ') });
  }
  if (!context.issues.length) visit(context, source);
  return { issues: context.issues, callables: context.callables };
}

/**
 * Inventories authored script files without following repository symlinks.
 * @param {string} directory Absolute directory being traversed.
 * @param {string[]} files Mutable accumulator of recognized source paths.
 * @returns {void} Adds source files; filesystem errors fail the invocation.
 */
export function collectSources(directory, files) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    const excluded = isExcludedDirectory(path.relative(ROOT, target));
    if (entry.isDirectory() && !excluded) collectSources(target, files);
    else if (entry.isFile() && EXTENSIONS.test(entry.name)) files.push(target);
    else if (entry.isSymbolicLink() && !excluded
        && (EXTENSIONS.test(entry.name) || fs.statSync(target).isDirectory())) {
      throw new Error(`Source symlink cannot be inventoried safely: ${target}`);
    }
  }
}

/**
 * Runs a repository-wide scan and prints actionable diagnostics.
 * @returns {number} Zero on compliance and one on any failure.
 */
function main() {
  const files = [];
  collectSources(ROOT, files);
  files.sort();
  let functions = 0;
  let violations = 0;
  for (const filename of files) {
    const result = analyzeSource(filename, fs.readFileSync(filename, 'utf8'));
    functions += result.callables;
    violations += result.issues.length;
    for (const issue of result.issues) console.error(`${path.relative(ROOT, issue.file)}:${issue.line} [${issue.rule}] ${issue.message}`);
  }
  console.log(`Style inventory: ${files.length} files, ${functions} callables, ${violations} violations.`);
  return violations ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    process.exitCode = main();
  } catch (error) {
    console.error(`Style inventory failed closed: ${error.message}`);
    process.exitCode = 1;
  }
}
