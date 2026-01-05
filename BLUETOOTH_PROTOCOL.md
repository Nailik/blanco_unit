# Bluetooth GATT Services and Characteristics

---

Characteristics `3b531d4d-ed58-4677-b2fa-1c72a86082cf` used to sent and read jsons.

Write
{
    "session":7780315, # id of currently connected session
    "id":9077670, # request id, response contains the same
    "type":1, # type (1 seems to be request)
    "token":"993223dcf15d3865439a66ea4b10c576ea485ccf989b6e9c235acdd27bda8634", # token (sha256(sha256(pin)+salt))
    "salt":"77803159077670", # salt to generate token (session#id)
    "body":{
        "meta":{
            "dev_type":1,
            "evt_ts":1767457215710,
            "evt_type":10,
            "evt_ver":1
            },
        "pars":{
        }
    }
}

Read
{
    "session":7780315, # id of currently connected session
    "id":9077670, # rid from request
    "type":2, # type (2 seems to be response)
    "body":{
        "meta":{
            "dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
            "dev_type":1,
            "evt_ts":2706416986,
            "evt_type":10,
            "evt_ver":1,
            "res_type":2
        }
    }
}


known event types

| evt_type  | evt_ver  | opts ctrl | pars evt_type  | Description  |
|---|---|---|---|---|
| 10 | 1 |  - | - | Connection  |
| 7 | 1 | 3 |  | Version Information  |
| 7 | 1 | 3 |  5 | Calibration Information  |
| 7 | 1 | 2 | -  | Serial Information  |
| 7 | 1 | 3 | 6 | State Information  |
| 7 | 1 | 3 | 4 | Error Information  |




[BLE Write =>] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":9077670,"type":1,"token":"993223dcf15d3865439a66ea4b10c576ea485ccf989b6e9c235acdd27bda8634","salt":"77803159077670","body":{"meta":{"dev_type":1,"evt_ts":1767457215710,"evt_type":10,"evt_ver":1},"pars":{}}}

[BLE Read <=] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf  {"session":7780315,"id":9077670,"type":2,"body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":2706416986,"evt_type":10,"evt_ver":1,"res_type":2}}}

[BLE Write =>] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":7604844,"type":1,"token":"6cb618c3e6a95cef6a1178c68fb34d4fa44c0b6ec09142c073ab49bd70786311","salt":"77803157604844","body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":1767457216910,"evt_type":7,"evt_ver":1},"opts":{"ctrl":3},"pars":{"evt_type":2}}}

[BLE Read <=] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":7604844,"type":2,"body":{"results":[{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":2706418268,"evt_type":2,"evt_ver":1},"pars":{"sw_ver_comm_con":{"val":"3.1.5"},"sw_ver_elec_con":{"val":"101"},"sw_ver_main_con":{"val":"112"},"dev_name":{"val":"SODA-210"},"reset_cnt":{"val":5}}}]}}

[BLE Write =>] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":8284286,"type":1,"token":"ac69ef6221d96ccdcbfbd301ed4c3dd7e9aadcbbda53ca96b766c4d9e2373c62","salt":"77803158284286","body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":1767457218005,"evt_type":7,"evt_ver":1},"opts":{"ctrl":3},"pars":{"evt_type":5}}}

[BLE Read <=] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":8284286,"type":2,"body":{"results":[{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":2706419558,"evt_type":5,"evt_ver":1},"pars":{"calib_still_wtr":{"val":500},"calib_soda_wtr":{"val":500},"filter_life_tm":{"val":560},"post_flush_quantity":{"val":40},"set_point_cooling":{"val":5},"wtr_hardness":{"val":1}}}]}}

[BLE Write =>] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":7594209,"type":1,"token":"c0c5353ef58c1d9ab9e6895ceb68060ad592d2ca26df1612d3424a6c02f40697","salt":"77803157594209","body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":1767457219648,"evt_type":7,"evt_ver":1},"opts":{"ctrl":2},"pars":{}}}

[BLE Read <=] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":7594209,"type":2,"body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":2706420995,"evt_type":3,"evt_ver":1,"act_type":4},"pars":{"ser_no":"25F2404-56210","serv_code":"75895"}}}

[BLE Write =>] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":3070034,"type":1,"token":"17f4d66fcc9b9428e372450ecbb705fa1455de135d2a2c2ebcfaf9610ce52fb0","salt":"77803153070034","body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":1767457220826,"evt_type":7,"evt_ver":1},"opts":{"ctrl":3},"pars":{"evt_type":6}}}

[BLE Read <=] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":3070034,"type":2,"body":{"results":[{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":2706422191,"evt_type":6,"evt_ver":1},"pars":{"tap_state":{"val":0},"filter_rest":{"val":37},"co2_rest":{"val":90},"wtr_disp_active":{"val":false},"firm_upd_avlb":{"val":false},"set_point_cooling":{"val":5},"clean_mode_state":{"val":0},"err_bits":{"val":0}}}]}}

[BLE Write =>] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":3469654,"type":1,"token":"8233afd326d15d581e0ee2f31427156d5764c2bdf467251c9971a88db5f5d3cc","salt":"77803153469654","body":{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":1767457221996,"evt_type":7,"evt_ver":1},"opts":{"ctrl":3},"pars":{"evt_type":4}}}

[BLE Read <=] UUID: 3b531d4d-ed58-4677-b2fa-1c72a86082cf {"session":7780315,"id":3469654,"type":2,"body":{"results":[{"meta":{"dev_id":"52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039","dev_type":1,"evt_ts":2706424036,"evt_type":4,"evt_ver":1},"pars":{"errs":[]}}]}}
