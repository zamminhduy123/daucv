import { notFound } from "next/navigation";
import { nganhNgheList } from "@/app/mau-cv/[nganh-nghe]/page";
import TemplateViewApp from "@/components/workspace/TemplateViewApp";

export default async function AppTemplatePage({
  params,
}: {
  params: Promise<{ "nganh-nghe": string }>;
}) {
  const { "nganh-nghe": slug } = await params;

  const data = nganhNgheList[slug as keyof typeof nganhNgheList];

  if (!data) notFound();

  return <TemplateViewApp data={data} />;
}
