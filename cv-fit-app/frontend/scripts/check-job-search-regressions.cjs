/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require("node:assert/strict");
const createJiti = require("jiti");

const jiti = createJiti(__filename, { interopDefault: true });
const { buildJobSearchQueries, sanitizeSearchProfile } = jiti("../src/lib/jobs/query.ts");
const { searchViaSearchEngine } = jiti("../src/lib/jobs/job-sources/search-engine.ts");
const { rankJobs } = jiti("../src/lib/jobs/rank.ts");

async function main() {
  const profile = {
    targetRoles: ["Frontend Developer"],
    seniority: "junior",
    skills: ["React", "TypeScript", "Next.js"],
    location: "Hà Nội",
    yearsOfExperience: 2,
  };

  const queries = buildJobSearchQueries(profile, [
    "digital marketing remote",
    "frontend developer",
    "reactjs developer",
  ]);

  assert.equal(queries[0], "frontend developer react hà nội");
  assert.ok(!queries.includes("digital marketing remote"));
  assert.ok(queries.some(query => query.includes("react")));

  const mlProfile = {
    targetRoles: ["Machine Learning Engineer"],
    seniority: "junior",
    skills: ["JavaScript", "TypeScript"],
    location: "Hồ Chí Minh",
    yearsOfExperience: 2,
  };

  const mlQueries = buildJobSearchQueries(mlProfile, [
    "machine learning engineer javascript",
    "typescript machine learning engineer",
    "machine learning engineer",
  ]);

  assert.equal(mlQueries[0], "machine learning engineer hồ chí minh");
  assert.ok(mlQueries.includes("machine learning engineer"));
  assert.ok(mlQueries.every(query => !query.includes("javascript")));
  assert.ok(mlQueries.every(query => !query.includes("typescript")));

  const sanitizedMlProfile = sanitizeSearchProfile(mlProfile);
  assert.deepEqual(sanitizedMlProfile.targetRoles, ["Frontend Developer"]);

  const rankedMlJobs = rankJobs([
    {
      id: "ml-1",
      source: "topcv",
      title: "AI/ML Engineer",
      company: "Tech Company",
      location: "Hồ Chí Minh",
      salary: "Thoả thuận",
      level: "junior",
      skills: ["Python", "PyTorch", "Deep Learning", "SQL", "Docker"],
      postedText: "Hôm nay",
      url: "https://example.com/job",
      descriptionSnippet: "Build machine learning models with Python, PyTorch and SQL.",
    },
  ], {
    targetRoles: ["Machine Learning Engineer"],
    seniority: "junior",
    skills: ["Python", "PyTorch", "Machine Learning", "SQL"],
    location: "Hồ Chí Minh",
    yearsOfExperience: 2,
  });

  assert.equal(rankedMlJobs[0].matchLabel, "good_match");
  assert.ok(rankedMlJobs[0].matchScore >= 70);

  delete process.env.SERPER_API_KEY;
  delete process.env.GOOGLE_API_KEY;
  delete process.env.GOOGLE_CSE_ID;

  const noKeyJobs = await searchViaSearchEngine("React Developer", "topcv.vn", 3);
  assert.equal(noKeyJobs.length, 0);

  process.env.SERPER_API_KEY = "test-key";
  const originalFetch = global.fetch;
  global.fetch = async () => ({
    ok: true,
    json: async () => ({
      organic: [
        {
          title: "Glints Job Explore",
          link: "https://glints.com/vn/opportunities/jobs/explore?keyword=react",
          snippet: "Browse hiring opportunities",
        },
        {
          title: "Frontend Developer - Acme | Glints",
          link: "https://glints.com/vn/opportunities/jobs/frontend-developer-acme/123456",
          snippet: "Tuyển Frontend Developer React TypeScript tại Hà Nội.",
        },
      ],
    }),
  });

  try {
    const liveJobs = await searchViaSearchEngine("React Developer", "glints.com/vn/opportunities", 4);
    assert.equal(liveJobs.length, 1);
    assert.equal(liveJobs[0].url, "https://glints.com/vn/opportunities/jobs/frontend-developer-acme/123456");
  } finally {
    global.fetch = originalFetch;
    delete process.env.SERPER_API_KEY;
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
