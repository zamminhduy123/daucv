const EMAIL_PATTERN = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g;
const PHONE_PATTERN = /(?:\+?\d[\d\s().-]{6,}\d)/g;
const LINK_PATTERN = /(?:https?:\/\/|www\.)[^\s|•,;]+|(?:linkedin|github)\.com\/[^\s|•,;]+/gi;
const CONTACT_LABELS = new Set([
  "email",
  "e-mail",
  "phone",
  "tel",
  "telephone",
  "mobile",
  "website",
  "web",
  "linkedin",
  "github",
]);

/**
 * @typedef {object} ParsedLegacyContacts
 * @property {string | null} email
 * @property {string | null} phone
 * @property {string[]} links
 * @property {string[]} residual
 */

/**
 * @param {string[]} lines
 * @returns {ParsedLegacyContacts}
 */
export function parseLegacyContactLines(lines) {
  const contacts = lines.map((line) => line.trim()).filter(Boolean);
  const emails = contacts.flatMap((line) => Array.from(line.matchAll(EMAIL_PATTERN), (match) => match[0]));
  const phones = contacts
    .flatMap((line) => Array.from(line.matchAll(PHONE_PATTERN), (match) => match[0].trim()))
    .filter((candidate) => candidate.replace(/\D/g, "").length >= 8);
  const links = contacts
    .flatMap((line) => Array.from(line.matchAll(LINK_PATTERN), (match) => match[0].replace(/[.)\]]+$/, "")))
    .filter((link, index, all) => all.indexOf(link) === index);
  const residual = contacts
    .flatMap(unparsedContactFragments)
    .filter((fragment, index, all) => all.indexOf(fragment) === index);

  return {
    email: emails[0] ?? null,
    phone: phones[0] ?? null,
    links,
    residual,
  };
}

/**
 * @param {import("@/types").CVIdentity} identity
 * @returns {string[]}
 */
export function identityContactLines(identity) {
  const parsed = parseLegacyContactLines(identity.contact_lines || []);
  const canonical = [
    identity.email || parsed.email,
    identity.phone || parsed.phone,
    identity.location,
    ...((identity.links || []).length ? identity.links : parsed.links),
  ].filter(Boolean);
  return [...canonical, ...parsed.residual]
    .filter((value, index, all) => all.indexOf(value) === index);
}

/**
 * @param {string} line
 * @returns {string[]}
 */
function unparsedContactFragments(line) {
  const withoutEmail = line.replace(EMAIL_PATTERN, "");
  const withoutPhone = withoutEmail.replace(
    PHONE_PATTERN,
    (match) => match.replace(/\D/g, "").length >= 8 ? "" : match,
  );
  const residual = withoutPhone.replace(LINK_PATTERN, "");

  return residual
    .split(/\s*(?:\||•|·|;)\s*/)
    .map((part) => part.replace(/^[\s|•·;,-]+|[\s|•·;,-]+$/g, ""))
    .filter((fragment) => Boolean(fragment) && !CONTACT_LABELS.has(fragment.replace(/:$/, "").trim().toLowerCase()));
}
