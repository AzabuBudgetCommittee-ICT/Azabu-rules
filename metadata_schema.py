from enum import Enum

from pydantic import BaseModel, Field, model_validator

RULE_ID_PATTERN = r"^\d{4}(?:CON|LAW|RUL)\d{7}$"
REVISION_ID_PATTERN = (
    r"^\d{4}(?:CON|LAW|RUL)\d{7}_(?:\d{8}|XXXXXXXX)_(?:\d{4}(?:CON|LAW|RUL)\d{7}|0{14}|X{14})$"
)

class RuleType(Enum):
    """
    CONstitution：規約
    LAW：規程
    RULe: 規則
    """

    CON = "CON"
    LAW = "LAW"
    RUL = "RUL"

class RuleStatus(Enum):
    """
    Effective: 有効
    Repeal: 廃止
    Expire: 失効
    Suspend: 停止
    """
    EFFECTIVE = 0
    REPEAL = 1
    EXPIRE = 2
    SUSPEND = 3

class RevisionInfo(BaseModel):
    """
    revision_id: READMEに定めた通りの改正id
    enforcement_date: 施行日が確定している場合は、revision_idに記載されているのと同じ形式で日付を入れる。未定であればXXXXXXXXを、不明であれば00000000を入れる。
    enforcement_comment: 施行日が未定な場合、その施行日に関する規定内容（例：本会議で議決された日から一年を超えない範囲で法制局規則で定める日）
    """

    revision_id: str = Field(pattern=REVISION_ID_PATTERN)
    enforcement_date: str = Field(pattern=r"^(?:\d{8}|XXXXXXXX)$")
    enforcement_comment: str | None = None

    @model_validator(mode="after")
    def validate_enforcement_date_matches_revision_id(self) -> "RevisionInfo":
        revision_date = self.revision_id.split("_")[1]
        if self.enforcement_date != revision_date:
            raise ValueError("enforcement_date must match revision_id date segment")
        return self

class Metadata(BaseModel):
    """
    rule_id: 規則類id
    rule_name: 規則類名
    rule_name_kana: rule_nameと対応して、規則類の読みを登録
    rule_name_abbrev: 規則名の省略形
    rule_name_abbrev_kana: abbrevと対応して、略称の読みを登録
    current_revision_id: 現在有効な改正id
    revision_info: 改正情報
    """

    rule_id: str = Field(pattern=RULE_ID_PATTERN)
    rule_type: RuleType
    rule_status: RuleStatus
    rule_name: str
    rule_name_kana: str | None = None
    rule_name_abbrev: list[str]
    rule_name_abbrev_kana: list[str] | None = None
    current_revision_id: str = Field(pattern=REVISION_ID_PATTERN)
    revision_info: list[RevisionInfo]

    @model_validator(mode="after")
    def validate_abbrev_kana_length(self) -> "Metadata":
        if self.rule_name_abbrev_kana is not None and (
            len(self.rule_name_abbrev_kana) != len(self.rule_name_abbrev)
        ):
            raise ValueError("rule_name_abbrev_kana must have the same length as rule_name_abbrev")
        revision_ids = {revision.revision_id for revision in self.revision_info}
        if self.current_revision_id not in revision_ids:
            raise ValueError("current_revision_id must exist in revision_info")
        return self