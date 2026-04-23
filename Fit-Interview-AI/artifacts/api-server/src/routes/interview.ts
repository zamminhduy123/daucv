import { Router, type IRouter, type Request, type Response } from "express";
import { openai } from "@workspace/integrations-openai-ai-server";
import { InterviewChatBody, InterviewChatResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.post("/interview/chat", async (req: Request, res: Response): Promise<void> => {
  const parsed = InterviewChatBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { jd_text, cv_text, chat_history } = parsed.data;

  try {
    const messages = [
      {
        role: "system" as const,
        content: `You are a professional interviewer conducting a job interview for the following position:

Job Description:
${jd_text}

Candidate's CV:
${cv_text}

Instructions:
- Ask one technical or behavioral question at a time
- Keep the conversation professional yet conversational
- Briefly evaluate the candidate's previous answer before asking the next question (1-2 sentences)
- Ask questions that are directly relevant to the job requirements
- Start by introducing yourself and asking the first question if this is the beginning of the interview
- After 8-10 questions, wrap up the interview professionally with brief feedback`,
      },
      ...chat_history.map((msg) => ({
        role: msg.role as "user" | "assistant" | "system",
        content: msg.content,
      })),
    ];

    const completion = await openai.chat.completions.create({
      model: "gpt-5.2",
      max_completion_tokens: 1024,
      messages,
    });

    const content = completion.choices[0]?.message?.content;
    if (!content) {
      res.status(500).json({ error: "No response from AI" });
      return;
    }

    const result = InterviewChatResponse.parse({ message: content });
    res.json(result);
  } catch (err) {
    req.log.error({ err }, "Error in interview chat");
    res.status(500).json({ error: "Failed to get interview response" });
  }
});

export default router;
