import { Router, type IRouter } from "express";
import healthRouter from "./health";
import cvRouter from "./cv";
import interviewRouter from "./interview";

const router: IRouter = Router();

router.use(healthRouter);
router.use(cvRouter);
router.use(interviewRouter);

export default router;
