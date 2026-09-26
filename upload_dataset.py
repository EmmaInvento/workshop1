from project_1.upload_dataset import (
    CASES_FILE,
    DATASET_NAME,
    load_cases,
    upload_golden_set,
)

if __name__ == "__main__":
    upload_golden_set(load_cases(CASES_FILE), DATASET_NAME)