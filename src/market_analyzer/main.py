    stress_input=returns.reindex(columns=portfolio["tic"]).fillna(0.0).to_numpy()
    stress_model=TimeGANStressTester(feature_dim=stress_input.shape[1],hidden_dim=16,sequence_length=20,seed=42)
    stress_model.fit(stress_input,epochs=5,batch_size=128)
    stress_report=stress_model.evaluate(paths=100,weights=stress_weights)
    stress_summary=asdict(stress_report)
    brief=build_market_brief(signals,portfolio)
    from market_analyzer.dashboard.app import set_state
    set_state(signals=signals[signals["date"]==signals["date"].max()].to_dict("records"),portfolio=portfolio.to_dict("records"),brief=brief,backtest=backtest_summary,stress=stress_summary)
    return {"features":features,"walk_forward_forecasts":forecasts,"ensemble_history":history,"signals":signals,"portfolio":portfolio,"brief":brief,"backtest":backtest,"backtest_summary":backtest_summary,"stress":stress_summary,"walk_forward_windows":windows}
