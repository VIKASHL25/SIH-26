import os
import numpy as np
import pandas as pd
from realtime_rul_predictor import RealTimeRULPredictor
from simulate_realtime_engine import simulate_engine

# ============================================================
# SETTINGS
# ============================================================

ENGINE_LIFETIMES=[
    100.0,
    250.0,
    400.0,
    550.0,
    700.0,
    850.0,
    950.0
]

MISSION_TYPES=[
    "normal",
    "mixed",
    "high_load",
    "hot_weather",
    "harsh"
]

MASTER_SEED=42

CURRENT_DIR=os.path.dirname(
    os.path.abspath(__file__)
)

OUTPUT_FILE=os.path.join(
    CURRENT_DIR,
    "..",
    "data",
    "multi_engine_rul_evaluation.csv"
)

# ============================================================
# METRIC FUNCTION
# ============================================================

def calculate_metrics(
    actual,
    predicted
):

    actual=np.asarray(
        actual,
        dtype=float
    )

    predicted=np.asarray(
        predicted,
        dtype=float
    )

    error=(
        predicted-
        actual
    )

    mae=np.mean(
        np.abs(error)
    )

    rmse=np.sqrt(
        np.mean(
            error**2
        )
    )

    ss_res=np.sum(
        (
            actual-
            predicted
        )**2
    )

    ss_tot=np.sum(
        (
            actual-
            np.mean(actual)
        )**2
    )

    if ss_tot==0:

        r2=np.nan

    else:

        r2=(
            1-
            ss_res/
            ss_tot
        )

    return (
        mae,
        rmse,
        r2
    )

# ============================================================
# MAIN
# ============================================================

if __name__=="__main__":

    print("====================================")
    print("MULTI-ENGINE REAL-TIME RUL EVALUATION")
    print("====================================")

    print(
        "Engines tested:",
        len(ENGINE_LIFETIMES)
    )

    print(
        "Lifetimes:",
        ENGINE_LIFETIMES
    )

    print("====================================")

    all_results=[]

    engine_summary=[]

    # ========================================================
    # TEST EACH ENGINE
    # ========================================================

    for engine_number,lifetime in enumerate(
        ENGINE_LIFETIMES,
        start=1
    ):

        mission=MISSION_TYPES[
            (
                engine_number-1
            )%len(MISSION_TYPES)
        ]

        engine_id=(
            f"EVAL_ENGINE_{engine_number:03d}"
        )

        seed=(
            MASTER_SEED+
            engine_number*
            100
        )

        print("\n------------------------------------")

        print(
            f"Engine: {engine_id}"
        )

        print(
            f"Lifetime: {lifetime:.1f} h"
        )

        print(
            f"Mission: {mission}"
        )

        print("------------------------------------")

        predictor=RealTimeRULPredictor()

        simulation=simulate_engine(
            engine_id,
            lifetime,
            mission,
            seed
        )

        engine_results=[]

        for (
            record,
            actual_rul,
            degradation,
            health_index
        ) in simulation:

            prediction=(
                predictor.predict(
                    record
                )
            )

            if (
                prediction["status"]
                !="PREDICTED"
            ):

                continue

            predicted_rul=float(
                prediction[
                    "rul_hours"
                ]
            )

            timestamp=float(
                record[
                    "timestamp_hours"
                ]
            )

            engine_results.append({
                "engine_id":engine_id,
                "lifetime_hours":lifetime,
                "mission_type":mission,
                "timestamp_hours":timestamp,
                "actual_rul_hours":actual_rul,
                "predicted_rul_hours":predicted_rul,
                "raw_rul_hours":prediction.get(
                    "raw_rul_hours",
                    predicted_rul
                ),
                "error_hours":(
                    predicted_rul-
                    actual_rul
                ),
                "absolute_error_hours":abs(
                    predicted_rul-
                    actual_rul
                ),
                "degradation":degradation,
                "health_index":health_index,
                "health_status":prediction[
                    "health_status"
                ]
            })

        engine_df=pd.DataFrame(
            engine_results
        )

        if len(engine_df)==0:

            print(
                "No predictions generated."
            )

            continue

        # ====================================================
        # OVERALL ENGINE METRICS
        # ====================================================

        (
            overall_mae,
            overall_rmse,
            overall_r2
        )=calculate_metrics(
            engine_df[
                "actual_rul_hours"
            ],
            engine_df[
                "predicted_rul_hours"
            ]
        )

        # ====================================================
        # EARLY LIFE
        # RUL >= 75% OF LIFETIME
        # ====================================================

        early=engine_df[
            engine_df[
                "actual_rul_hours"
            ]>=(
                0.75*
                lifetime
            )
        ]

        if len(early)>0:

            early_mae=np.mean(
                early[
                    "absolute_error_hours"
                ]
            )

        else:

            early_mae=np.nan

        # ====================================================
        # MID LIFE
        # 25%-75% RUL
        # ====================================================

        middle=engine_df[
            (
                engine_df[
                    "actual_rul_hours"
                ]>=(
                    0.25*
                    lifetime
                )
            )
            &
            (
                engine_df[
                    "actual_rul_hours"
                ]<(
                    0.75*
                    lifetime
                )
            )
        ]

        if len(middle)>0:

            middle_mae=np.mean(
                middle[
                    "absolute_error_hours"
                ]
            )

        else:

            middle_mae=np.nan

        # ====================================================
        # END OF LIFE
        # RUL <= 10% OF LIFETIME
        # ====================================================

        end=engine_df[
            engine_df[
                "actual_rul_hours"
            ]<=(
                0.10*
                lifetime
            )
        ]

        if len(end)>0:

            end_mae=np.mean(
                end[
                    "absolute_error_hours"
                ]
            )

        else:

            end_mae=np.nan

        # ====================================================
        # FINAL PREDICTION
        # ====================================================

        final_row=(
            engine_df.iloc[-1]
        )

        final_actual=float(
            final_row[
                "actual_rul_hours"
            ]
        )

        final_predicted=float(
            final_row[
                "predicted_rul_hours"
            ]
        )

        final_error=(
            final_predicted-
            final_actual
        )

        # ====================================================
        # SAVE SUMMARY
        # ====================================================

        engine_summary.append({
            "engine_id":engine_id,
            "lifetime_hours":lifetime,
            "mission_type":mission,
            "overall_mae_hours":overall_mae,
            "overall_rmse_hours":overall_rmse,
            "overall_r2":overall_r2,
            "early_life_mae_hours":early_mae,
            "middle_life_mae_hours":middle_mae,
            "end_of_life_mae_hours":end_mae,
            "final_actual_rul_hours":final_actual,
            "final_predicted_rul_hours":final_predicted,
            "final_error_hours":final_error,
            "final_health_status":final_row[
                "health_status"
            ]
        })

        all_results.extend(
            engine_results
        )

        print(
            f"MAE: {overall_mae:.2f} h"
        )

        print(
            f"RMSE: {overall_rmse:.2f} h"
        )

        if np.isnan(overall_r2):

            print(
                "R2: N/A"
            )

        else:

            print(
                f"R2: {overall_r2:.4f}"
            )

        print(
            f"Early-life MAE: "
            f"{early_mae:.2f} h"
        )

        print(
            f"Mid-life MAE: "
            f"{middle_mae:.2f} h"
        )

        print(
            f"End-of-life MAE: "
            f"{end_mae:.2f} h"
        )

        print(
            f"Final actual RUL: "
            f"{final_actual:.2f} h"
        )

        print(
            f"Final predicted RUL: "
            f"{final_predicted:.2f} h"
        )

        print(
            f"Final error: "
            f"{final_error:.2f} h"
        )

        print(
            f"Final health: "
            f"{final_row['health_status']}"
        )

    # ========================================================
    # COMBINE RESULTS
    # ========================================================

    results_df=pd.DataFrame(
        all_results
    )

    summary_df=pd.DataFrame(
        engine_summary
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    summary_file=os.path.join(
        CURRENT_DIR,
        "..",
        "data",
        "multi_engine_rul_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False
    )

    # ========================================================
    # GLOBAL METRICS
    # ========================================================

    (
        global_mae,
        global_rmse,
        global_r2
    )=calculate_metrics(
        results_df[
            "actual_rul_hours"
        ],
        results_df[
            "predicted_rul_hours"
        ]
    )

    # ========================================================
    # GLOBAL EARLY/MIDDLE/END
    # ========================================================

    early_global=results_df[
        results_df[
            "actual_rul_hours"
        ]>=(
            0.75*
            results_df[
                "lifetime_hours"
            ]
        )
    ]

    middle_global=results_df[
        (
            results_df[
                "actual_rul_hours"
            ]>=(
                0.25*
                results_df[
                    "lifetime_hours"
                ]
            )
        )
        &
        (
            results_df[
                "actual_rul_hours"
            ]<(
                0.75*
                results_df[
                    "lifetime_hours"
                ]
            )
        )
    ]

    end_global=results_df[
        results_df[
            "actual_rul_hours"
        ]<=(
            0.10*
            results_df[
                "lifetime_hours"
            ]
        )
    ]

    early_global_mae=np.mean(
        early_global[
            "absolute_error_hours"
        ]
    )

    middle_global_mae=np.mean(
        middle_global[
            "absolute_error_hours"
        ]
    )

    end_global_mae=np.mean(
        end_global[
            "absolute_error_hours"
        ]
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print("\n====================================")
    print("GLOBAL EVALUATION")
    print("====================================")

    print(
        "Total prediction records:",
        len(results_df)
    )

    print(
        "Engines:",
        len(summary_df)
    )

    print()

    print(
        f"GLOBAL MAE : "
        f"{global_mae:.2f} hours"
    )

    print(
        f"GLOBAL RMSE: "
        f"{global_rmse:.2f} hours"
    )

    print(
        f"GLOBAL R2  : "
        f"{global_r2:.4f}"
    )

    print()

    print(
        f"EARLY-LIFE MAE: "
        f"{early_global_mae:.2f} hours"
    )

    print(
        f"MID-LIFE MAE: "
        f"{middle_global_mae:.2f} hours"
    )

    print(
        f"END-OF-LIFE MAE: "
        f"{end_global_mae:.2f} hours"
    )

    print("\n====================================")
    print("ENGINE SUMMARY")
    print("====================================")

    print(
        summary_df[
            [
                "engine_id",
                "lifetime_hours",
                "mission_type",
                "overall_mae_hours",
                "early_life_mae_hours",
                "middle_life_mae_hours",
                "end_of_life_mae_hours",
                "final_predicted_rul_hours"
            ]
        ].to_string(
            index=False
        )
    )

    print("\n====================================")
    print("FILES CREATED")
    print("====================================")

    print(
        os.path.abspath(
            OUTPUT_FILE
        )
    )

    print(
        os.path.abspath(
            summary_file
        )
    )

    print("\n====================================")
    print("EVALUATION COMPLETE")
    print("====================================")