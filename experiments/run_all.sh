#!/usr/bin/env bash
# Chạy lại mọi số liệu chính thức của WM1, WM2, WM3, WM5, WM6 trong experiments/results.md, một lượt.
#
#     bash experiments/run_all.sh                 # log ở data/logs/run_all-<ngày giờ>/
#     ONLY='wm2_v3|wm3_stars' bash experiments/run_all.sh   # chỉ chạy các bước có tên khớp regex
#
# Không crawl, không gửi request ra ngoài. Cần: dữ liệu trong data/ (snapshot, nhãn), Label Studio local
# đang chạy (chỉ cho κ WM1), GPU nếu phải train lại PhoBERT (bỏ qua nếu model đã có).
# Mỗi bước ghi một file log; bước lỗi không dừng cả lượt, cuối cùng in danh sách bước lỗi.
set -u
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
LOG="data/logs/run_all-$(date +%Y%m%d-%H%M)"
mkdir -p "$LOG"
FAILED=()

step() {  # step <tên> <lệnh…>
  local name=$1; shift
  [[ -n "${ONLY:-}" && ! "$name" =~ $ONLY ]] && return 0
  echo "== $name: $*" | tee -a "$LOG/_tong.txt"
  local t0=$SECONDS
  if "$@" >"$LOG/$name.txt" 2>&1; then
    echo "   ok ($((SECONDS - t0)) giây)" | tee -a "$LOG/_tong.txt"
  else
    echo "   LỖI ($((SECONDS - t0)) giây) – xem $LOG/$name.txt" | tee -a "$LOG/_tong.txt"
    FAILED+=("$name")
  fi
}
py() { uv run python -m "$@"; }

echo "commit: $(git rev-parse --short HEAD)$(git diff --quiet HEAD -- . ':!data' || echo -dirty)" | tee "$LOG/_tong.txt"

# WM1 – dedup. Baseline: khóa tiêu đề + công ty. So: v1 (∪ MinHash), v2 (tiêu đề mềm ∪ MinHash cắt khung).
step wm1_dedup_nhan01  py crawler.eval_dedup
step wm1_dedup_nhan02  py crawler.eval_dedup --labels data/annotation/dedup_batch1.labels_v02.jsonl
step wm1_kappa         py annotation.kappa_dedup score --from-ls 11

# WM2 – trích kỹ năng. Baseline: từ điển alias. Hệ chính: PhoBERT nhãn yếu v3 (chốt 2026-11-18), 3 seed;
# PhoBERT v1 giữ làm dòng so sánh (số cũ). Train lại chỉ khi thiếu model.
step wm2_dict_test     py ie.baseline_dict --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --snapshot topcv_v1
for s in 1 2 3; do
  [ -f "data/models/wm2-phobert-s$s/config.json" ] || step "wm2_train_s$s" py ie.phobert train --weak v1 --seed "$s"
  step "wm2_phobert_test_s$s" py ie.phobert eval --model "data/models/wm2-phobert-s$s" --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed "$s"
done
step wm2_paired        py experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl
for s in 1 2 3; do
  [ -f "data/models/wm2-phobert-v3-s$s/config.json" ] || step "wm2_v3_train_s$s" py ie.phobert train --weak v3 --seed "$s"
  step "wm2_v3_test_s$s" py ie.phobert eval --weak v3 --model "data/models/wm2-phobert-v3-s$s" --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed "$s"
done
step wm2_v3_paired     py experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl --prefix wm2-phobert-v3 --out data/eval/skill_test1_preds_v3.json
step wm2_diag          py experiments.diag_wm2
step wm2_kappa         py annotation.kappa_skill

# WM3 – ABSA. Baseline: từ điển v3; mốc phụ: luật một dòng theo `section`. So: mô hình lai (từ điển + TF-IDF + LR).
step wm3_cv            py absa.supervised cv --model all
step wm3_test          py absa.supervised test --model hybrid
step wm3_paired_dict   py experiments.paired_wm3
step wm3_paired_sect   py experiments.paired_wm3 --baseline section
step wm3_diag          py experiments.diag_wm3
step wm3_stars         py absa.company_eval --b 2000
step wm3_kappa         py annotation.kappa_absa --a data/annotation/absa_test1.absa.jsonl --b data/annotation/absa_kappa1_p2.absa.jsonl

# WM5 – gợi ý việc làm. Baseline: độ phổ biến. So: content-tfidf, hybrid. Log synthetic v2 (sinh lại, seed cố định).
step wm5_events        py recsys.events
step wm5_reco          py recsys.baseline --eval-set reco_v2

# WM6 – đồ thị kỹ năng. Mốc: bậc có trọng số, đồ thị ngẫu nhiên giữ bậc, phép đếm đồng xuất hiện.
step wm6_build         py graph.build --extractor dict
step wm6_rank          py graph.analyze rank
step wm6_cluster       py graph.analyze cluster --min-npmi 0.3 --n-null 100
step wm6_stability     py graph.analyze stability --split source --min-npmi 0.3
step wm6_rank_npmi     py graph.analyze rank --weight npmi
step wm6_recommend     py graph.recommend

# Nhu cầu kỹ năng (thống kê mô tả, không có baseline).
step demand_top        py experiments.skill_demand --top 10 --min-jobs 15
step demand_all        py experiments.skill_demand --all-categories

echo | tee -a "$LOG/_tong.txt"
if [ ${#FAILED[@]} -eq 0 ]; then echo "Xong, không bước nào lỗi. Log: $LOG" | tee -a "$LOG/_tong.txt"
else echo "Bước lỗi: ${FAILED[*]}. Log: $LOG" | tee -a "$LOG/_tong.txt"; exit 1; fi
