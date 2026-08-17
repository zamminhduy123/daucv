"""Raw PDF extraction models and extraction decision schemas."""

from enum import Enum

from pydantic import BaseModel, Field

RAW_EXTRACTION_CONTENT_TYPE = "application/vnd.daucv.raw-extraction+json"


class ExtractionMethod(str, Enum):
    NATIVE_BLOCKS = "native_blocks"
    WORD_LAYOUT = "word_layout"
    OCR = "ocr"
    MANUAL_TEXT = "manual_text"


class ExtractionReason(str, Enum):
    TEXT_TOO_SHORT = "text_too_short"
    TOO_FEW_ALNUM_CHARACTERS = "too_few_alnum_characters"
    NO_TEXT_BLOCKS = "no_text_blocks"
    SUSPICIOUS_SINGLE_BLOCK = "suspicious_single_block"
    POSSIBLE_COLUMN_INTERLEAVING = "possible_column_interleaving"
    IMAGE_ONLY_PAGE = "image_only_page"
    CORRUPTED_TEXT = "corrupted_text"


class RawBlock(BaseModel):
    """A canonical raw text block extracted from a PDF page."""

    block_id: str
    page: int = Field(ge=1)
    text: str
    bbox: tuple[float, float, float, float] | None = None
    extraction_method: ExtractionMethod
    reading_order: int = Field(default=0, ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class RawPage(BaseModel):
    """Raw extraction content for a single PDF page."""

    page: int = Field(ge=1)
    width: float | None = None
    height: float | None = None
    blocks: list[RawBlock] = Field(default_factory=list)


class RawExtraction(BaseModel):
    """Complete raw text extraction from a PDF file."""

    extraction_version: str = "2.0"
    method: ExtractionMethod
    pages: list[RawPage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExtractionDecision(BaseModel):
    """Usability evaluation decision for an extraction result."""

    usable: bool
    recommended_method: ExtractionMethod
    reasons: list[ExtractionReason] = Field(default_factory=list)


class OCRNotAvailableError(Exception):
    """Raised when PDF extraction requires OCR but OCR engine is not integrated."""

    def __init__(self, message: str = "The uploaded PDF appears to require OCR."):
        self.message = message
        self.code = "OCR_NOT_AVAILABLE"
        super().__init__(self.message)


class InvalidRawExtractionError(ValueError):
    """Raised when RawExtraction contains invalid or duplicate block IDs."""

    pass


class InvalidRawExtractionArtifactError(ValueError):
    """Raised when a stored file reference is not a valid raw extraction."""

    pass
