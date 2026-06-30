import { CandidateProfile } from "../jobs/types";

// Standard technical skills to search for in CV
const SKILLS_DICTIONARY = [
  "javascript", "typescript", "html", "css", "sass", "less", "tailwind", "bootstrap",
  "react", "reactjs", "react native", "vue", "vuejs", "angular", "next.js", "nextjs",
  "nodejs", "express", "expressjs", "nestjs", "fastapi", "django", "flask", "laravel",
  "spring boot", "spring", "asp.net", ".net core", "c#", "java", "python", "golang", "go",
  "php", "ruby", "rails", "swift", "kotlin", "flutter", "dart", "rust", "c++", "c",
  "sql", "mysql", "postgresql", "postgres", "mongodb", "nosql", "redis", "firebase",
  "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "jenkins", "git", "github", "gitlab",
  "ci/cd", "figma", "ui/ux", "scrum", "agile", "testing", "qa", "qc", "jest", "cypress",
  "selenium", "machine learning", "deep learning", "ai", "nlp", "data analysis"
];

// Target roles and their matching keywords
const ROLE_KEYWORDS: Record<string, string[]> = {
  "Frontend Developer": ["frontend", "front-end", "front end", "react developer", "web developer", "ui developer"],
  "Backend Developer": ["backend", "back-end", "back end", "nodejs developer", "java developer", "python developer", "php developer"],
  "Fullstack Developer": ["fullstack", "full-stack", "full stack", "fullstack developer", "fullstack engineer"],
  "Mobile Developer": ["mobile", "android", "ios", "react native", "flutter", "swift", "kotlin"],
  "DevOps Engineer": ["devops", "sre", "system admin", "cloud engineer", "aws engineer"],
  "Data Engineer": ["data engineer", "data engineering", "etl", "big data"],
  "AI Engineer": ["ai engineer", "ai developer", "ai research", "nlp", "ai/ml", "generative ai"],
  "Machine Learning Engineer": ["ml engineer", "machine learning engineer", "deep learning engineer", "machine learning", "deep learning"],
  "Data Scientist": ["data scientist", "data science", "statistician"],
  "QA/QC Tester": ["tester", "qa", "qc", "quality assurance", "test engineer", "manual test", "automation test"],
  "Business Analyst": ["business analyst", "ba", "product owner"],
  "Project Manager": ["project manager", "pm", "scrum master"]
};

// Seniority mappings
const SENIORITY_KEYWORDS = {
  intern: ["intern", "thực tập", "thực tập sinh", "internship"],
  fresher: ["fresher", "mới tốt nghiệp", "entry level", "no experience"],
  junior: ["junior", "dưới 2 năm", "1 năm kinh nghiệm", "1 year experience", "junior developer"],
  middle: ["middle", "mid-level", "2 năm kinh nghiệm", "3 năm kinh nghiệm", "2 years experience", "3 years experience"],
  senior: ["senior", "trưởng nhóm", "lead", "4 năm kinh nghiệm", "5 năm kinh nghiệm", "4 years experience", "5 years experience", "senior developer"]
};

export function parseCV(cvText: string): CandidateProfile {
  if (!cvText) {
    return {
      targetRoles: [],
      seniority: "unknown",
      skills: [],
      location: undefined,
      summary: ""
    };
  }

  const normalizedText = cvText.toLowerCase();

  // 1. Extract Skills
  const skills: string[] = [];
  SKILLS_DICTIONARY.forEach(skill => {
    // Escape special characters in skill name (like .net, c++)
    const escaped = skill.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
    // Ensure word boundaries or custom boundary check
    let regex: RegExp;
    if (skill === "c" || skill === "go") {
      // For single/very short letters, make sure they are isolated words
      regex = new RegExp(`\\b${escaped}\\b`, "i");
    } else if (skill.includes("+") || skill.includes(".")) {
      // For skills like c++, next.js
      regex = new RegExp(`(?:\\b|\\s|^)${escaped}(?:\\b|\\s|$|,)`, "i");
    } else {
      regex = new RegExp(`\\b${escaped}\\b`, "i");
    }

    if (regex.test(normalizedText)) {
      // Capitalize first letter of each word for clean presentation
      const formatted = skill
        .split(" ")
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
      skills.push(formatted);
    }
  });

  // 2. Infer Target Roles
  const targetRolesMap = new Map<string, number>();
  Object.entries(ROLE_KEYWORDS).forEach(([role, keywords]) => {
    keywords.forEach(keyword => {
      const escaped = keyword.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
      const regex = new RegExp(`\\b${escaped}\\b`, "gi");
      const matches = normalizedText.match(regex);
      if (matches) {
        targetRolesMap.set(role, (targetRolesMap.get(role) || 0) + matches.length);
      }
    });
  });

  // Sort target roles by frequency of mention
  const targetRoles = Array.from(targetRolesMap.entries())
    .sort((a, b) => b[1] - a[1])
    .map(entry => entry[0]);

  // Default to a general role if none found
  if (targetRoles.length === 0) {
    targetRoles.push("Software Engineer");
  }

  // 3. Infer Seniority Level
  let seniority: CandidateProfile["seniority"] = "unknown";
  let maxSeniorityScore = -1;
  let yearsOfExperience = 0;

  // Extract years of experience using both English and Vietnamese patterns
  const engExpRegex = /(\d+)\s*(?:year|yr)s?\s*(?:of\s*)?experience/gi;
  const viExpRegex = /(\d+)\s*năm\s*kinh\s*nghiệm/gi;
  
  const engMatch = engExpRegex.exec(normalizedText);
  const viMatch = viExpRegex.exec(normalizedText);
  const matchedYears = engMatch || viMatch;

  if (matchedYears) {
    yearsOfExperience = parseInt(matchedYears[1], 10);
    // Prioritize seniority based on years of experience
    if (yearsOfExperience >= 5) seniority = "senior";
    else if (yearsOfExperience >= 3) seniority = "middle";
    else if (yearsOfExperience >= 1) seniority = "junior";
    else seniority = "fresher";
  }

  // If no years of experience pattern found, fall back to keyword frequency counting
  if (seniority === "unknown") {
    Object.entries(SENIORITY_KEYWORDS).forEach(([level, keywords]) => {
      let score = 0;
      keywords.forEach(keyword => {
        const escaped = keyword.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
        const regex = new RegExp(`\\b${escaped}\\b`, "gi");
        const matches = normalizedText.match(regex);
        if (matches) {
          score += matches.length;
        }
      });

      if (score > maxSeniorityScore && score > 0) {
        maxSeniorityScore = score;
        seniority = level as CandidateProfile["seniority"];
      }
    });
  }

  // 4. Location Preference
  let location: string | undefined = undefined;
  const cities = [
    { name: "Hồ Chí Minh", keys: ["hồ chí minh", "ho chi minh", "hcm", "sài gòn", "saigon"] },
    { name: "Hà Nội", keys: ["hà nội", "ha noi", "hn"] },
    { name: "Đà Nẵng", keys: ["đà nẵng", "da nang", "dn"] }
  ];

  for (const city of cities) {
    const isMatched = city.keys.some(key => normalizedText.includes(key));
    if (isMatched) {
      location = city.name;
      break;
    }
  }

  // 5. Generate Summary
  // Extract the first 3 lines or 150 chars as a summary
  const summary = cvText.slice(0, 150).trim() + "...";

  return {
    targetRoles,
    seniority,
    skills,
    location,
    summary,
    yearsOfExperience
  };
}
