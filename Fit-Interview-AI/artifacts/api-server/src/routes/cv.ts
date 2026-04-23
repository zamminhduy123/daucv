import { Router, type IRouter, type Request, type Response } from "express";
import { openai } from "@workspace/integrations-openai-ai-server";
import { AnalyzeCVBody, AnalyzeCVResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.post("/cv/analyze", async (req: Request, res: Response): Promise<void> => {
  const parsed = AnalyzeCVBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { cv_text, jd_text } = parsed.data;

  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-5.2",
      max_completion_tokens: 8192,
      messages: [
        {
          role: "system",
          content: `You are an expert HR Manager and career coach. Compare the provided CV and Job Description carefully. 
Return a JSON object with exactly these fields:
- "match_score": integer 0-100 representing how well the CV matches the JD
- "missing_skills": array of strings listing key skills/qualifications the CV lacks compared to the JD
- "tailored_cv": a JSON object with:
  - "name": candidate's full name (string)
  - "summary": a rewritten professional summary tailored to the JD (string)
  - "experience": array of objects, each with "company" (string), "role" (string), "bullet_points" (array of strings rewritten to highlight JD requirements)
  - "education": education section as a string
  - "skills": array of skill strings relevant to the JD

Return ONLY the JSON object with no markdown code blocks or extra text.`,
        },
        {
          role: "user",
          content: `CV:\n${cv_text}\n\nJob Description:\n${jd_text}`,
        },
      ],
    });

    const content = completion.choices[0]?.message?.content;
    if (!content) {
      res.status(500).json({ error: "No response from AI" });
      return;
    }

    let parsed_result;
    try {
      parsed_result = JSON.parse(content);
    } catch {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        res.status(500).json({ error: "Failed to parse AI response as JSON" });
        return;
      }
      parsed_result = JSON.parse(jsonMatch[0]);
    }

    const validated = AnalyzeCVResponse.safeParse(parsed_result);
    if (!validated.success) {
      req.log.warn({ errors: validated.error.message }, "AI response validation failed, returning raw");
      res.json(parsed_result);
      return;
    }

    res.json(validated.data);
  } catch (err) {
    req.log.error({ err }, "Error analyzing CV");
    res.status(500).json({ error: "Failed to analyze CV" });
  }
});

export default router;
