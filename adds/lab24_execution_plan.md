# Lab 24 Execution Plan - MedViet Governance

## Mục tiêu trong ngày

Hoàn thành bài lab **Data Governance & Security for AI Platform** cho MedViet, đạt tối thiểu mức pass 70/100 và ưu tiên các hạng mục nhiều điểm: PII Detection, Anonymization, RBAC API, Encryption, Security Audit, Compliance Checklist.

## Nguyên tắc thực hiện

- Làm theo thứ tự phụ thuộc: data -> PII/anonymization -> tests -> RBAC/API -> encryption -> quality -> security/compliance -> reports.
- Mỗi phase phải có output kiểm chứng được bằng test, command, file report hoặc checklist.
- Không nộp `data/raw/`, `.vault_key`, credential hoặc file secret thật.
- Giữ thay đổi tập trung trong `medviet-governance/`; ghi chú phụ trợ để trong `adds/`.

## Phase 0 - Baseline & Setup

**Mục tiêu:** Nắm trạng thái hiện tại của repo và chuẩn bị môi trường chạy lab.

**Việc cần làm:**

- Kiểm tra cấu trúc project so với README.
- Kiểm tra `requirements.txt`, `.gitignore`, thư mục `data/`, `reports/`, `policies/`, `tests/`.
- Cài dependency cần thiết trong virtual environment.
- Xác nhận các file TODO chính:
  - `src/pii/detector.py`
  - `src/pii/anonymizer.py`
  - `tests/test_pii.py`
  - `src/access/rbac.py`
  - `src/api/main.py`
  - `src/encryption/vault.py`
  - `src/quality/validation.py`
  - `policies/opa_policy.rego`
  - `compliance_checklist.md`

**Milestone:**

- Chạy được `python --version` và import các package chính.
- Có `.gitignore` loại trừ `.vault_key`, `data/raw/`, `reports/` nếu cần, cache và virtualenv.

**Definition of Done:**

- Repo ở trạng thái sẵn sàng chạy script và test.
- Không có blocker dependency rõ ràng.

## Phase 1 - Data Preparation

**Mục tiêu:** Tạo dataset giả lập và xác định rõ cột PII.

**Việc cần làm:**

- Chạy `scripts/generate_data.py` để sinh `data/raw/patients_raw.csv`.
- Kiểm tra số lượng record, schema, vài dòng đầu.
- Liệt kê các cột chứa PII:
  - `ho_ten`
  - `cccd`
  - `ngay_sinh`
  - `so_dien_thoai`
  - `email`
  - `dia_chi`
  - `bac_si_phu_trach`
- Phân loại cột cần giữ cho model training:
  - Giữ nguyên: `patient_id`, `benh`, `ket_qua_xet_nghiem`, `ngay_kham`
  - Anonymize/replace: các cột PII

**Milestone:**

- File `medviet-governance/data/raw/patients_raw.csv` tồn tại và có khoảng 200 records.

**Definition of Done:**

- Dataset đọc được bằng pandas.
- Có danh sách PII dùng cho detection rate và anonymization.

## Phase 2 - PII Detection & Anonymization

**Mục tiêu:** Đạt detection rate >= 95% và đảm bảo PII gốc không còn trong output.

**Việc cần làm:**

- Hoàn thiện `src/pii/detector.py`:
  - Regex CCCD Việt Nam: 12 chữ số.
  - Regex số điện thoại Việt Nam: `0[35789]` + 8 chữ số.
  - Analyzer hỗ trợ entity: `PERSON`, `EMAIL_ADDRESS`, `VN_CCCD`, `VN_PHONE`.
  - Nếu spaCy Vietnamese model khó cài, dùng fallback hợp lý để vẫn pass tests cho lab.
- Hoàn thiện `src/pii/anonymizer.py`:
  - Strategy `replace` bằng Faker.
  - Strategy `mask`.
  - Strategy `hash` bằng SHA-256 nếu cần.
  - `anonymize_dataframe()` xử lý từng cột PII đúng yêu cầu.
  - `calculate_detection_rate()` tính tỷ lệ detect trên các cột PII.
- Hoàn thiện `tests/test_pii.py`:
  - Test CCCD, phone, email.
  - Test detection rate >= 95%.
  - Test CCCD gốc không còn trong output.
  - Test non-PII columns giữ nguyên.

**Milestone:**

- `pytest tests/test_pii.py -v --tb=short` pass.
- Tạo được `data/processed/patients_anonymized.csv`.

**Definition of Done:**

- Detection rate >= 95%.
- Không còn CCCD gốc trong dataframe anonymized.
- `benh` và `ket_qua_xet_nghiem` không đổi.

## Phase 3 - RBAC With Casbin & FastAPI

**Mục tiêu:** API phân quyền đúng theo vai trò, trả 403 ở các case bị cấm.

**Việc cần làm:**

- Kiểm tra và hoàn thiện `src/access/policy.csv`:
  - `admin`: full quyền patient data và model artifacts.
  - `ml_engineer`: đọc training data, đọc/ghi model artifacts, không đọc raw PII, không delete production.
  - `data_analyst`: đọc aggregated metrics, ghi reports, không đọc raw PII.
  - `intern`: chỉ sandbox.
- Hoàn thiện `src/access/rbac.py`:
  - Parse Bearer token.
  - Trả 401 nếu thiếu/sai token.
  - Dùng Casbin enforce role-resource-action.
  - Trả 403 khi không đủ quyền.
- Hoàn thiện `src/api/main.py`:
  - `/health`
  - `/api/patients/raw`
  - `/api/patients/anonymized`
  - `/api/metrics/aggregated`
  - `DELETE /api/patients/{patient_id}`
- Chạy manual smoke test bằng curl hoặc FastAPI TestClient.

**Milestone:**

- Bob gọi raw patient data nhận 403.
- Alice gọi raw patient data nhận 200.
- Bob delete patient nhận 403.

**Definition of Done:**

- API chạy được bằng `uvicorn src.api.main:app --reload`.
- Quyền truy cập đúng với README.

## Phase 4 - Encryption Vault

**Mục tiêu:** Implement envelope encryption local, round-trip thành công.

**Việc cần làm:**

- Hoàn thiện `src/encryption/vault.py`:
  - Load hoặc tạo KEK từ `.vault_key`.
  - Generate DEK.
  - Encrypt DEK bằng KEK.
  - Encrypt plaintext bằng DEK với AES-256-GCM.
  - Decrypt payload về plaintext ban đầu.
  - Encrypt một cột dataframe thành JSON payload.
- Đảm bảo `.vault_key` không bị commit.

**Milestone:**

- Round-trip pass:
  - input: `"Nguyen Van A - CCCD: 012345678901"`
  - decrypt(encrypt(input)) == input

**Definition of Done:**

- Encryption/decryption hoạt động.
- Không lưu plaintext key trong source code.

## Phase 5 - Data Quality Validation

**Mục tiêu:** Có validation layer cho anonymized patient data.

**Việc cần làm:**

- Hoàn thiện `src/quality/validation.py`:
  - `patient_id` không null.
  - `cccd` đúng format sau anonymization hoặc không còn raw CCCD gốc.
  - `ket_qua_xet_nghiem` nằm trong `[0, 50]`.
  - `benh` thuộc danh sách hợp lệ.
  - `email` match regex email hoặc được replace hợp lệ.
  - `patient_id` unique.
- Implement `validate_anonymized_data(filepath)`.
- Chạy validation trên `data/processed/patients_anonymized.csv`.

**Milestone:**

- Hàm validation trả về `success: true` hoặc liệt kê failed checks rõ ràng.

**Definition of Done:**

- Có kiểm tra chất lượng dữ liệu tối thiểu trước khi nộp.

## Phase 6 - OPA Policy

**Mục tiêu:** Hoàn thiện ABAC policy cho các role và rule data localization.

**Việc cần làm:**

- Hoàn thiện `policies/opa_policy.rego`:
  - Admin allow all.
  - ML Engineer đọc/ghi training data và model artifacts.
  - Data Analyst đọc aggregated metrics và ghi reports.
  - Intern chỉ access sandbox.
  - Deny export restricted data ra ngoài Việt Nam.
- Nếu có OPA CLI, chạy test eval các case chính.

**Milestone:**

- Case `ml_engineer` delete `production_data` trả `false`.
- Case restricted data ra nước ngoài bị deny.

**Definition of Done:**

- Policy rõ ràng, khớp RBAC và compliance story.

## Phase 7 - Security Scanning & Reports

**Mục tiêu:** Có bằng chứng security audit để nộp.

**Việc cần làm:**

- Tạo `.github/hooks/pre-commit`.
- Cấu hình git-secrets patterns cho CCCD, password, secret key và AWS.
- Chạy Bandit:
  - `bandit -r src/ -f json -o reports/bandit_report.json`
- Chạy TruffleHog nếu tool có sẵn:
  - `trufflehog git file://. --only-verified > reports/trufflehog_report.txt`
- Chạy pytest và lưu kết quả:
  - `pytest tests/ -v --tb=short > reports/test_results.txt`

**Milestone:**

- Có thư mục `reports/` với:
  - `test_results.txt`
  - `bandit_report.json`
  - `trufflehog_report.txt` nếu chạy được

**Definition of Done:**

- Có evidence cho phần Security Audit.
- Nếu tool nào không cài được, ghi rõ trong report hoặc final notes.

## Phase 8 - Compliance Checklist & Submission

**Mục tiêu:** Hoàn thiện checklist NĐ13/ISO 27001 mapping và chuẩn bị gói nộp.

**Việc cần làm:**

- Hoàn thiện `compliance_checklist.md`:
  - Data localization.
  - Explicit consent.
  - Breach notification 72h.
  - DPO appointment.
  - Technical controls mapping.
  - Mô tả solution cụ thể cho Audit logging và Breach detection.
- Kiểm tra deliverables:
  - `src/`
  - `tests/`
  - `policies/`
  - `data/processed/`
  - `compliance_checklist.md`
  - `reports/`
  - `requirements.txt`
- Tạo zip submission.

**Milestone:**

- Gói `lab24_submission_<ten_sv>.zip` tạo thành công.

**Definition of Done:**

- Không include `data/raw/`, `.vault_key`, credentials hoặc secret thật.
- Bài nộp có đủ code, policy, processed data, report và checklist.

## Timeline Gợi Ý Cho 3-4 Giờ

| Thời lượng | Phase | Output chính |
|---:|---|---|
| 15 phút | Phase 0-1 | Env sẵn sàng, raw dataset có dữ liệu |
| 60 phút | Phase 2 | PII/anonymization pass tests |
| 45 phút | Phase 3 | RBAC API chạy đúng quyền |
| 30 phút | Phase 4 | Encryption round-trip pass |
| 20 phút | Phase 5 | Validation chạy được |
| 20 phút | Phase 6 | OPA policy hoàn chỉnh |
| 25 phút | Phase 7 | Test/security reports |
| 25 phút | Phase 8 | Checklist và zip submission |

## Risk Log

| Rủi ro | Ảnh hưởng | Cách xử lý |
|---|---|---|
| Không cài được `vi_core_news_lg` | PII PERSON có thể fail | Dùng Presidio pattern/fallback phù hợp với test data |
| Great Expectations API khác version | Validation lỗi runtime | Implement validation thủ công trước, GX suite là bonus |
| Thiếu git-secrets/trufflehog/opa CLI | Không tạo được một số report | Ghi rõ tool unavailable, vẫn tạo Bandit và pytest report |
| Path chạy command sai do project nằm trong `medviet-governance/` | Import/file not found | Chạy command từ đúng thư mục hoặc set `PYTHONPATH` |
| Raw data bị nộp nhầm | Trừ điểm compliance/security | Kiểm tra zip bằng lệnh list trước khi nộp |

## Priority Nếu Thiếu Thời Gian

1. Phase 2: PII Detection & Anonymization.
2. Phase 3: RBAC API.
3. Phase 4: Encryption.
4. Phase 8: Compliance Checklist.
5. Phase 7: Reports, ưu tiên pytest và Bandit.
6. Phase 5-6: Quality và OPA hoàn thiện ở mức đủ chạy.

## Final Acceptance Checklist

- [ ] `patients_raw.csv` được sinh local nhưng không nằm trong submission.
- [ ] `patients_anonymized.csv` được tạo trong `data/processed/`.
- [ ] `pytest tests/ -v --tb=short` pass hoặc có report lỗi rõ ràng.
- [ ] Detection rate >= 95%.
- [ ] API trả 401/403/200 đúng case.
- [ ] Encryption round-trip pass.
- [ ] OPA policy hoàn thiện.
- [ ] `compliance_checklist.md` không còn TODO quan trọng.
- [ ] `reports/` có test/security evidence.
- [ ] Zip submission không chứa `.vault_key`, `data/raw/`, secret thật.
