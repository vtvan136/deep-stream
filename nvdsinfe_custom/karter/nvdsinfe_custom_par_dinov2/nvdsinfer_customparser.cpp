#include "nvdsinfer_custom_impl.h"
#include <vector>
#include <cstring>
#include <iostream>
#include <cstdlib>   // for strdup
#include <cmath>     // for expf

extern "C"
bool NvDsInferParseMultiTask(
    std::vector<NvDsInferLayerInfo> const &outputLayersInfo,
    NvDsInferNetworkInfo const &networkInfo,
    float classifierThreshold,
    std::vector<NvDsInferAttribute> &attrList,
    std::string &descString)
{
    const NvDsInferLayerInfo *ageLayer = nullptr;
    const NvDsInferLayerInfo *phoneLayer = nullptr;

    for (auto &l : outputLayersInfo) {
        if (!strcmp(l.layerName, "age_logits"))
            ageLayer = &l;
        else if (!strcmp(l.layerName, "phone_logits"))
            phoneLayer = &l;
    }

    if (!ageLayer || !phoneLayer) {
        std::cerr << "Missing output layers age_logits or phone_logits" << std::endl;
        return false;
    }

    float* ageBuf   = reinterpret_cast<float*>(ageLayer->buffer);
    float* phoneBuf = reinterpret_cast<float*>(phoneLayer->buffer);

    // Softmax for age logits (assuming 2 classes)
    float age_exp0 = std::exp(ageBuf[0]);
    float age_exp1 = std::exp(ageBuf[1]);
    float age_sum  = age_exp0 + age_exp1;
    float age_p0   = age_exp0 / age_sum;
    float age_p1   = age_exp1 / age_sum;

    // Softmax for phone logits (assuming 2 classes)
    float phone_exp0 = std::exp(phoneBuf[0]);
    float phone_exp1 = std::exp(phoneBuf[1]);
    float phone_sum  = phone_exp0 + phone_exp1;
    float phone_p0   = phone_exp0 / phone_sum;
    float phone_p1   = phone_exp1 / phone_sum;

    // Class indices: 0 = age, 1 = phone
    unsigned int age_class   = (age_p0 > age_p1) ? 0u : 1u;
    unsigned int phone_class = (phone_p0 > phone_p1) ? 0u : 1u;

    float age_conf   = (age_class == 0u) ? age_p0   : age_p1;
    float phone_conf = (phone_class == 0u) ? phone_p0 : phone_p1;

    // Only push if above threshold, or always push if you want
    if (age_conf   < classifierThreshold) age_class   = (unsigned int)(-1);
    if (phone_conf < classifierThreshold) phone_class = (unsigned int)(-1);

    NvDsInferAttribute attr1 = {};
    attr1.attributeLabel      = strdup("age");
    attr1.attributeIndex      = age_class;
    attr1.attributeValue      = age_class;
    attr1.attributeConfidence = age_conf;

    NvDsInferAttribute attr2 = {};
    attr2.attributeLabel      = strdup("phone");
    attr2.attributeIndex      = phone_class;
    attr2.attributeValue      = phone_class;
    attr2.attributeConfidence = phone_conf;

    attrList.push_back(attr1);
    attrList.push_back(attr2);

    descString = "age_phone";

    return true;
}

CHECK_CUSTOM_CLASSIFIER_PARSE_FUNC_PROTOTYPE(NvDsInferParseMultiTask);
